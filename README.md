# Unity Scripts for Quest Pro Data Collection

This folder contains all the Unity C# scripts needed for collecting head and eye tracking data from Quest Pro.

## Scripts Overview

### 1. `InvertSphere.cs`
- **Purpose**: Flips a sphere mesh so it can be viewed from inside (required for 360° video)
- **Usage**: Attach to any GameObject with a MeshFilter containing a sphere mesh
- **When to use**: Attach to your VideoSphere GameObject

### 2. `DataCollector.cs`
- **Purpose**: Main data collection script - records head tracking, eye tracking, and combined metrics
- **Dependencies**: Requires Camera (VR camera), VideoPlayer
- **Output**: Creates 3 CSV files per video:
  - `head_[participantID]_[videoID]_[timestamp].csv` - Head tracking data
  - `eye_[participantID]_[videoID]_[timestamp].csv` - Eye tracking data
  - `combined_[participantID]_[videoID]_[timestamp].csv` - Combined head+eye metrics
- **Settings**:
  - `participantID`: Participant identifier (e.g., "P001")
  - `videoID`: Video identifier (e.g., "video_01")
  - `recordData`: Toggle recording on/off
  - `recordingRate`: Sampling rate in Hz (default: 90 Hz for Quest Pro)

### 3. `VideoManager.cs`
- **Purpose**: Manages video playlist and automatic playback
- **Dependencies**: Requires VideoPlayer, DataCollector
- **Features**:
  - Loads videos from list (URLs or local files)
  - Auto-advances to next video when current ends
  - Updates DataCollector with current video ID
- **Settings**:
  - `videoURLs`: List of video file paths/URLs
  - `videoIDs`: List of video identifiers (must match videoURLs)
  - `delayBetweenVideos`: Seconds to wait between videos
  - `autoPlayNext`: Automatically play next video

### 4. `ParticipantSetup.cs`
- **Purpose**: Simple UI for entering participant ID before data collection
- **Dependencies**: Requires UI Canvas with InputField and Button
- **Features**:
  - Input field for participant ID
  - Start button to begin data collection
  - Saves participant ID to PlayerPrefs
  - Loads data collection scene

## Setup Instructions

### Step 1: Copy Scripts to Unity Project
1. Copy all `.cs` files from this folder
2. Paste into your Unity project: `Assets/Scripts/` folder
3. Unity will compile automatically

### Step 2: Set Up Scene Hierarchy
```
Scene
├── XR Origin (Action-based)
│   └── Camera Offset
│       └── Main Camera
├── Directional Light
├── VideoSphere (Sphere GameObject)
│   ├── Mesh Renderer
│   ├── Video Player (Component)
│   └── InvertSphere (Script)
└── DataCollectionManager (Empty GameObject)
    ├── DataCollector (Script)
    └── VideoManager (Script)
```

### Step 3: Configure Components

#### VideoSphere:
1. Position: (0, 0, 0)
2. Scale: (100, 100, 100)
3. Add Component → Video Player
4. Add Component → InvertSphere (script)

#### DataCollectionManager:
1. Add Component → DataCollector
2. Add Component → VideoManager
3. In DataCollector:
   - VR Camera: Drag Main Camera from XR Origin
   - Video Player: Drag VideoSphere
   - Participant ID: "P001" (change per participant)
   - Video ID: "video_01"
4. In VideoManager:
   - Video Player: Drag VideoSphere
   - Data Collector: Drag DataCollectionManager
   - Add video URLs and IDs in Inspector

### Step 4: Configure Videos

#### Option A: Local Files on Quest Pro
1. Copy videos to Quest Pro: `/sdcard/Movies/VRStudy/`
2. In VideoManager, add URLs like:
   ```
   file:///sdcard/Movies/VRStudy/video1.mp4
   file:///sdcard/Movies/VRStudy/video2.mp4
   ```
3. Add corresponding video IDs:
   ```
   video_01
   video_02
   ```

#### Option B: Videos in Unity Project
1. Import videos into `Assets/Videos/`
2. In VideoPlayer, assign VideoClip directly
3. VideoManager will use VideoClip source

## Data Output Format

### Head Tracking CSV
```
Timestamp,PlaybackTime,UnitQuaternion.x,UnitQuaternion.y,UnitQuaternion.z,UnitQuaternion.w,HmdPosition.x,HmdPosition.y,HmdPosition.z,FrameNumber,Yaw,Pitch,Roll,YawVelocity,PitchVelocity,RollVelocity
```

### Eye Tracking CSV
```
Timestamp,PlaybackTime,FrameNumber,GazeDirection.x,GazeDirection.y,GazeDirection.z,GazeYaw,GazePitch,LeftPupilDiameter,RightPupilDiameter,LeftEyeOpenness,RightEyeOpenness,LeftEyeConfidence,RightEyeConfidence,IsFixating,IsSaccade,FixationDuration,AveragePupilDiameter,TrackingQuality
```

### Combined CSV
```
Timestamp,PlaybackTime,FrameNumber,HeadYaw,HeadPitch,HeadRoll,GazeYaw,GazePitch,GazeRelativeHorizontal,GazeRelativeVertical,PupilAverage,EyeHeadOffsetAngle,EyeLeading,HeadFollowing,Aligned
```

## Troubleshooting

### Eye Tracking Not Working
- Check Quest Pro settings: Eye Tracking must be ON
- Recalibrate eye tracking in Quest Pro settings
- Verify Meta XR SDK is installed correctly
- Check Unity Console for errors

### Videos Not Playing
- Verify video format: MP4 (H.264 codec)
- Check video file path is correct
- Ensure video file exists on Quest Pro
- Try lower resolution video first

### Data Not Saving
- Check app has storage permissions
- Verify `Application.persistentDataPath` is writable
- Check disk space on Quest Pro
- Look at Unity Console for file write errors

### Build Errors
- Ensure all scripts are in `Assets/Scripts/` folder
- Check for compilation errors in Unity Console
- Verify all references are assigned in Inspector
- Make sure Unity 2022.3 LTS is being used

## Notes

- Data files are saved to: `/sdcard/Android/data/com.yourname.vrdatacollector/files/DataCollection/`
- Use ADB or SideQuest to retrieve files
- CSV files are created per video session
- Timestamps are in local time
- PlaybackTime is video playback time in seconds

## Next Steps

1. Test with one video first
2. Verify data files are created correctly
3. Check data format matches your requirements
4. Prepare all videos for collection
5. Run pilot study
6. Collect data from participants
