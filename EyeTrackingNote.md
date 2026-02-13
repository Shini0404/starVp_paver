# Important Note: Quest Pro Eye Tracking API

## Current Implementation

The `DataCollector.cs` script uses Unity's XR Input system to access eye tracking. However, **Quest Pro eye tracking may require Meta's specific SDK APIs**.

## Two Approaches:

### Approach 1: Unity XR Input (Current Implementation)
- Uses `InputDevice` with `EyeTracking` characteristics
- May work but might not have full Quest Pro features
- More portable across VR platforms

### Approach 2: Meta SDK Direct Access (Recommended for Quest Pro)
- Uses `OVRPlugin` or Meta XR SDK directly
- Full access to Quest Pro eye tracking features
- Quest Pro specific

## If Eye Tracking Doesn't Work:

### Option A: Use Meta XR SDK Directly

Replace the eye tracking code in `DataCollector.cs` with:

```csharp
using OVRPlugin;

// In InitializeEyeTracking():
bool eyeTrackingAvailable = OVRPlugin.GetSystemHeadsetType() == SystemHeadsetType.Quest_Pro;

// In TryGetEyeTrackingData():
EyeGazesState eyeGazesState;
bool success = OVRPlugin.GetEyeGazesState(Step.Render, -1, ref eyeGazesState);

if (success && eyeGazesState.IsValid[0]) // Left eye
{
    EyeGazeState leftEye = eyeGazesState.EyeGazes[0];
    // Access leftEye.Pose, leftEye.PupilDiameter, etc.
}
```

**Note**: This requires importing the Oculus Integration package or Meta XR SDK.

### Option B: Use Meta XR Interaction SDK

If you have Meta XR Interaction SDK installed:

```csharp
using Oculus.Interaction;

// Use EyeGrabber or EyeTracking components
// See Meta XR Interaction SDK documentation
```

### Option C: Head Tracking Only (Fallback)

If eye tracking continues to fail, you can:
1. Collect head tracking data only (which is still valuable)
2. Use head tracking as proxy for gaze (less accurate but works)
3. Add eye tracking later once SDK issues are resolved

## Troubleshooting Steps:

1. **Verify Eye Tracking is Enabled**:
   - Quest Pro Settings → Movement Tracking → Eye Tracking → ON
   - Recalibrate eye tracking

2. **Check Meta SDK Version**:
   - Window → Package Manager
   - Look for "Meta XR SDK" or "Oculus Integration"
   - Should be version 60+ for Quest Pro support

3. **Check Unity XR Settings**:
   - Edit → Project Settings → XR Plug-in Management
   - Oculus → Quest Pro should be checked

4. **Test in Unity Editor**:
   - Eye tracking won't work in editor
   - Must test on actual Quest Pro device

5. **Check Console Logs**:
   - Look for eye tracking initialization messages
   - Check for any errors related to eye tracking

## Recommended Solution:

For best Quest Pro support, use **Meta XR SDK directly** via `OVRPlugin`. This gives you:
- Full eye tracking access
- Pupil diameter
- Eye openness
- Confidence values
- All Quest Pro specific features

The current implementation is a starting point. If eye tracking doesn't work, switch to Meta SDK direct access.
