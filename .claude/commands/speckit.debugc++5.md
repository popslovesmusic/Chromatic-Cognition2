Debug this C++ audio processing code:
1. Check for audio buffer overflow/underflow
2. Verify sample rate and channel handling
3. Test parameter range validation (0-1, dB ranges, etc.)
4. Profile for real-time performance (no malloc in audio thread)
5. Check for thread safety in audio callback