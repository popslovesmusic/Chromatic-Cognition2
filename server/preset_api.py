"""
Preset REST API - FastAPI Endpoints

Implements FR-002, FR-003, FR-010: Complete REST API for preset management
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
import json
import io

from .preset_model import Preset, CollisionPolicy
from .preset_store import PresetStore
from .ab_snapshot import ABSnapshot


# Initialize stores (will be set by main app)
preset_store: Optional[PresetStore] = None
ab_manager: Optional[ABSnapshot] = None


def create_preset_api(store: PresetStore, ab: ABSnapshot) -> FastAPI:
    """
    Create FastAPI application with preset endpoints

    Args:
        store: PresetStore instance
        ab: ABSnapshot manager instance

    Returns:
        FastAPI application
    """
    app = FastAPI(title="Soundlab Preset API", version="1.0")

    # Store references
    global preset_store, ab_manager
    preset_store = store
    ab_manager = ab

    # --- CRUD Endpoints ---

    @app.get("/api/presets")
    async def list_presets(
        query: Optional[str] = Query(None, description="Search query (name/notes)"),
        tag: Optional[str] = Query(None, description="Filter by tag"),
        limit: int = Query(50, ge=1, le=200, description="Maximum results")
    ):
        """
        List presets with optional filtering

        Implements: GET /api/presets?query=&tag=&limit=50
        """
        try:
            presets = preset_store.list(query=query, tag=tag, limit=limit)
            return JSONResponse(content=presets)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/presets/{preset_id}")
    async def get_preset(preset_id: str):
        """
        Get full preset by ID

        Implements: GET /api/presets/{id}
        """
        preset = preset_store.load(preset_id)

        if preset is None:
            raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")

        return JSONResponse(content=preset.to_dict())

    @app.post("/api/presets")
    async def create_preset(
        preset_data: dict,
        collision: CollisionPolicy = Query("prompt", description="Collision resolution strategy")
    ):
        """
        Create/save a new preset

        Implements: POST /api/presets

        Body:
            - Full preset JSON, OR
            - {"name": "...", "collision": "prompt|overwrite|new_copy|merge"}
        """
        try:
            # Check if this is a simple name-only request
            if 'schema_version' not in preset_data:
                # Create new preset with just a name
                name = preset_data.get('name', 'Untitled')
                preset = Preset(name=name)
            else:
                # Full preset data provided
                preset = Preset.from_dict(preset_data)

            # Validate
            preset.validate()

            # Save
            preset_id, was_created = preset_store.create(preset, collision=collision)

            return JSONResponse(
                content={
                    'id': preset_id,
                    'created': was_created,
                    'name': preset.name
                },
                status_code=201 if was_created else 200
            )

        except FileExistsError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Validation error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.put("/api/presets/{preset_id}")
    async def update_preset(preset_id: str, preset_data: dict):
        """
        Update existing preset

        Implements: PUT /api/presets/{id}
        """
        try:
            preset = Preset.from_dict(preset_data)

            # Ensure ID matches
            if preset.id != preset_id:
                preset.id = preset_id

            # Validate
            preset.validate()

            # Update
            success = preset_store.update(preset)

            if not success:
                raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")

            return JSONResponse(content={'ok': True, 'id': preset_id})

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Validation error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/presets/{preset_id}")
    async def delete_preset(preset_id: str):
        """
        Delete preset by ID

        Implements: DELETE /api/presets/{id}
        """
        success = preset_store.delete(preset_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")

        return JSONResponse(content={'ok': True})

    # --- Import/Export Endpoints ---

    @app.post("/api/presets/export")
    async def export_all_presets():
        """
        Export all presets as JSON bundle

        Implements: POST /api/presets/export
        Returns: File download
        """
        try:
            bundle = preset_store.export_all()
            json_data = json.dumps(bundle, indent=2)

            # Create streaming response
            return StreamingResponse(
                io.BytesIO(json_data.encode()),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=soundlab_presets_export.json"
                }
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/presets/import")
    async def import_presets(
        file: UploadFile = File(...),
        dry_run: bool = Query(False, description="Validate only, don't save"),
        collision: CollisionPolicy = Query("prompt", description="Collision resolution")
    ):
        """
        Import preset bundle from JSON file

        Implements: POST /api/presets/import?dry_run=true|false&collision=...

        Returns:
            {
                'imported': int,
                'updated': int,
                'skipped': int,
                'errors': List[str]
            }
        """
        try:
            # Read uploaded file
            contents = await file.read()
            bundle = json.loads(contents)

            # Import bundle
            results = preset_store.import_bundle(
                bundle,
                collision=collision,
                dry_run=dry_run
            )

            return JSONResponse(content=results)

        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # --- A/B Snapshot Endpoints ---

    @app.post("/api/presets/ab/store/{slot}")
    async def store_ab_snapshot(slot: str, preset_data: dict):
        """
        Store current state in A or B slot

        Args:
            slot: 'A' or 'B'
            preset_data: Preset to store
        """
        if slot not in ['A', 'B']:
            raise HTTPException(status_code=400, detail="Slot must be 'A' or 'B'")

        try:
            preset = Preset.from_dict(preset_data)

            if slot == 'A':
                ab_manager.store_a(preset)
            else:
                ab_manager.store_b(preset)

            return JSONResponse(content={
                'ok': True,
                'slot': slot,
                'status': ab_manager.get_status()
            })

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/presets/ab/get/{slot}")
    async def get_ab_snapshot(slot: str):
        """
        Get snapshot from A or B slot

        Args:
            slot: 'A' or 'B'
        """
        if slot not in ['A', 'B']:
            raise HTTPException(status_code=400, detail="Slot must be 'A' or 'B'")

        preset = ab_manager.get_a() if slot == 'A' else ab_manager.get_b()

        if preset is None:
            raise HTTPException(status_code=404, detail=f"Slot {slot} is empty")

        return JSONResponse(content=preset.to_dict())

    @app.post("/api/presets/ab/toggle")
    async def toggle_ab():
        """
        Toggle between A and B snapshots

        Returns preset to apply or error if not possible
        """
        try:
            preset = ab_manager.toggle()

            if preset is None:
                raise HTTPException(
                    status_code=429,
                    detail=f"Toggle too fast (guard time: {ab_manager.CROSSFADE_GUARD_MS}ms)"
                )

            return JSONResponse(content={
                'ok': True,
                'current_slot': ab_manager.get_current_slot(),
                'preset': preset.to_dict()
            })

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/presets/ab/status")
    async def get_ab_status():
        """Get A/B comparison status"""
        status = ab_manager.get_status()
        return JSONResponse(content=status)

    @app.get("/api/presets/ab/diff")
    async def get_ab_diff():
        """Get differences between A and B"""
        diff = ab_manager.get_diff()

        if diff is None:
            raise HTTPException(status_code=400, detail="Cannot compare: A or B is empty")

        return JSONResponse(content=diff)

    @app.delete("/api/presets/ab/clear/{slot}")
    async def clear_ab_snapshot(slot: str):
        """Clear A, B, or both slots"""
        if slot == 'A':
            ab_manager.clear_a()
        elif slot == 'B':
            ab_manager.clear_b()
        elif slot == 'all':
            ab_manager.clear_all()
        else:
            raise HTTPException(status_code=400, detail="Slot must be 'A', 'B', or 'all'")

        return JSONResponse(content={'ok': True})

    # --- Statistics Endpoint ---

    @app.get("/api/presets/stats")
    async def get_preset_statistics():
        """Get preset store statistics"""
        stats = preset_store.get_statistics()
        return JSONResponse(content=stats)

    return app


# Standalone server for testing
if __name__ == "__main__":
    import uvicorn

    # Initialize stores
    store = PresetStore()
    ab = ABSnapshot()

    # Create app
    app = create_preset_api(store, ab)

    print("=" * 60)
    print("Preset API Test Server")
    print("=" * 60)
    print("\nStarting server at http://localhost:8000")
    print("API docs at http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)

    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
