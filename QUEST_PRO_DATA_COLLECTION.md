# Quest Pro Data Collection Guide for STAR-VP

## ⚠️ IMPORTANT: Unity Version Recommendation

**Use Unity 2022.3 LTS** (NOT 2021 LTS or latest version)

**Why Unity 2022.3 LTS?**
- ✅ Better Quest Pro eye tracking support
- ✅ More stable Meta XR SDK integration
- ✅ Better performance with 360° video
- ✅ Still LTS (Long Term Support) - stable and supported
- ✅ Compatible with Meta XR SDK 60+

**Unity 2021 LTS Issues:**
- ❌ Older eye tracking API (may not work well with Quest Pro)
- ❌ Compatibility issues with newer Meta SDK versions
- ❌ Missing Quest Pro specific optimizations

**Latest Unity Issues:**
- ❌ Too new - may have bugs
- ❌ Less tested with Quest Pro
- ❌ May have breaking changes

---

## PHASE 0: Prerequisites

### Hardware Checklist
```
✅ Meta Quest Pro headset (256GB)
✅ Quest Pro charging dock
✅ USB-C cable (for data transfer)
✅ Windows PC or Mac
   - Windows 10/11 (recommended) OR macOS
   - 16GB RAM recommended
   - 30GB free disk space
   - Graphics card: GTX 1060 or better
✅ Stable internet connection
```

### Software to Install
```
1. Meta Quest mobile app (for initial setup)
2. Unity Hub (latest version)
3. Unity Editor 2022.3 LTS
4. Meta XR All-in-One SDK (via Unity Package Manager)
5. Android Build Support for Unity
6. SideQuest (optional, for easier file transfer)
```

### Accounts Needed
```
1. Meta account (Facebook/Instagram linked)
2. Meta Developer account (free) - https://developer.oculus.com/
3. Unity account (free) - https://unity.com/
```

**Estimated Setup Time: 3-4 hours (first time)**

---

## PHASE 1: Quest Pro Initial Setup (30 minutes)

### Step 1.1: Unbox and Charge
```
1. Place Quest Pro AND controllers on charging dock
2. Plug into wall outlet
3. Wait 2 hours for full charge
```

### Step 1.2: Download Meta Quest Mobile App
```
1. iPhone: App Store → "Meta Quest"
2. Android: Google Play → "Meta Quest"
3. Download and open app
4. Log in with Meta account
```

### Step 1.3: Pair Quest Pro with Phone
```
1. Put on Quest Pro
2. Press power button (right side)
3. Wait for boot (~30 seconds)
4. Follow setup wizard
5. In phone app: "Add Headset" → "Quest Pro"
6. Enter pairing code from headset
7. Set up WiFi, guardian boundary, profile
```

### Step 1.4: Critical Settings
```
In Quest Pro headset:

1. Settings → System → Hand Tracking
   - Turn OFF "Auto Enable Hand Tracking"

2. Settings → Movement Tracking
   - Tracking: ON
   - Eye Tracking: ON
   - Face Tracking: ON (optional, for research)

3. Calibrate Eye Tracking:
   - Settings → Movement Tracking → Eye Tracking → Calibrate
   - Follow dots with eyes (30 seconds)
   - Aim for "Good" or "Excellent"

4. Adjust IPD:
   - Physical slider at bottom of headset
   - Adjust until clear
   - Note the number (e.g., 63mm)
   - Use same IPD for each participant

5. Update Firmware:
   - Settings → System → Software Update
   - Install all updates
   - Restart headset
```

---

## PHASE 2: Enable Developer Mode (15 minutes)

### Step 2.1: Create Developer Account
```
1. Go to: https://developer.oculus.com/
2. Sign Up/Log In with Meta account
3. Go to: https://dashboard.oculus.com/
4. Create Organization:
   - Name: "Research Lab" or your name
   - Accept Developer Agreement
5. ✅ Developer account created!
```

### Step 2.2: Enable Developer Mode
```
In Meta Quest mobile app:

1. Open Meta Quest app
2. Devices → Your Quest Pro
3. Developer Mode → Toggle ON
4. If not visible:
   - Wait 5-10 minutes after creating dev account
   - Close and reopen app
5. Restart Quest Pro
```

### Step 2.3: Verify Developer Mode
```
Put on Quest Pro:
- Should see "Developer Mode" text at bottom
- If not → Restart headset again
```

---

## PHASE 3: Install Unity 2022.3 LTS (1 hour)

### Step 3.1: Download Unity Hub
```
1. Go to: https://unity.com/download
2. Download Unity Hub
3. Install Unity Hub
4. Open Unity Hub
5. Sign in with Unity account (create if needed)
```

### Step 3.2: Install Unity 2022.3 LTS
```
In Unity Hub:

1. Installs → Install Editor
2. Select: Unity 2022.3.x LTS
   - Look for "2022.3" with "LTS" badge
   - Current: 2022.3.45 or similar
3. Click "Install"
4. In "Add modules" screen, CHECK:
   ☑ Android Build Support
      ├─☑ Android SDK & NDK Tools
      ├─☑ OpenJDK
      └─☑ Android SDK Platform Tools
   ☑ Documentation (optional)
5. UNCHECK everything else
6. Click "Continue" → Accept licenses → "Install"
7. Wait 30-60 minutes (downloads ~8GB)
```

### Step 3.3: Install Meta XR SDK
```
We'll install this via Unity Package Manager (easier and more reliable)
Skip manual download - we'll do it in Unity project
```

---

## PHASE 4: Create Unity Project (30 minutes)

### Step 4.1: Create New Project
```
In Unity Hub:

1. Projects → New Project
2. Template: "3D Core" (NOT URP/HDRP)
3. Project Name: "QuestProDataCollection"
4. Location: Choose location with space
5. Unity Version: 2022.3.x LTS
6. Click "Create Project"
7. Wait for Unity to open (2-3 minutes)
```

### Step 4.2: Switch to Android Platform
```
In Unity Editor:

1. File → Build Settings
2. Platform list → Click "Android"
3. Click "Switch Platform" (bottom right)
4. Wait 5-10 minutes
5. ✅ Android icon appears next to "Android"
```

### Step 4.3: Configure Android Build Settings
```
Still in Build Settings:

1. Click "Player Settings..." (bottom left)
2. In Inspector panel:

   A. Company Name: "YourName" or "ResearchLab"
   B. Product Name: "VRDataCollector"
   
   C. Other Settings:
      - Package Name: "com.yourname.vrdatacollector"
        (lowercase, no spaces, unique)
      - Minimum API Level: "Android 10.0 (API Level 29)"
      - Target API Level: "Android 13.0 (API Level 33)"
      - Scripting Backend: "IL2CPP" ⚠️ IMPORTANT!
      - ARM64 ☑ (check)
      - ARMv7 ☐ (uncheck)
   
   D. XR Plug-in Management:
      - Click "Install XR Plugin Management" if shown
      - Wait for installation
      - Click Android tab (small Android icon)
      - Check ☑ "Oculus"
      - Oculus settings appear below

3. Close Build Settings
4. File → Save Project (Ctrl+S / Cmd+S)
```

### Step 4.4: Install Meta XR SDK via Package Manager
```
In Unity Editor:

1. Window → Package Manager
2. Click "+" (top left) → "Add package from git URL"
3. Enter: com.meta.xr.sdk.all
4. Click "Add"
5. Wait 5-10 minutes
6. You should see packages:
   - Meta XR Core SDK
   - Meta XR Interaction SDK
   - Meta XR Platform SDK
   - Meta XR SDK
7. Close Package Manager
```

**If git URL doesn't work:**
```
Alternative method:

1. Window → Package Manager
2. Click "+" → "Add package from disk"
3. Download Meta SDK from:
   https://developer.oculus.com/downloads/package/meta-xr-sdk-all-in-one-upm/
4. Extract .tgz file
5. Navigate to extracted folder → package.json
6. Select package.json
7. Wait for import
```

### Step 4.5: Configure XR Settings
```
In Unity:

1. Edit → Project Settings
2. Left panel → XR Plug-in Management
3. Click "Oculus" section
4. Settings:
   ☑ Stereo Rendering Mode: "Multiview"
   ☑ Low Overhead Mode: OFF (for development)
   ☑ Phase Sync: ON
   ☑ Optimize Buffer Discards: ON
5. Scroll to "Quest Pro" in Devices
   ☑ Check "Quest Pro"
6. Close Project Settings
```

---

## PHASE 5: Create Data Collection Scene (1 hour)

### Step 5.1: Set Up Basic Scene
```
In Unity Hierarchy:

1. Delete "Main Camera" (we'll add XR camera)
2. Keep "Directional Light"
```

### Step 5.2: Add XR Rig
```
1. Hierarchy → Right-click → XR → "XR Origin (Action-based)"
   - Creates VR camera system

2. Hierarchy structure:
   XR Origin
   ├─ Camera Offset
   │  └─ Main Camera
   └─ (other components)

3. Select "XR Origin" in Hierarchy

4. Inspector:
   - Transform Position: (0, 0, 0)
   - Camera Y Offset: 1.6 (average eye height)

5. Save scene:
   File → Save As
   Name: "DataCollection"
   Location: Assets/Scenes/
```

### Step 5.3: Add 360 Video Sphere
```
1. Hierarchy → Right-click → 3D Object → Sphere
2. Name: "VideoSphere"
3. Select VideoSphere, Inspector:
   Transform:
   - Position: (0, 0, 0)
   - Rotation: (0, 0, 0)
   - Scale: (100, 100, 100) ← BIG!

4. Mesh Renderer:
   - Cast Shadows: OFF
   - Receive Shadows: OFF
```

### Step 5.4: Create Video Material
```
1. Project panel → Right-click → Create → Material
2. Name: "VideoMaterial"
3. Select VideoMaterial, Inspector:
   Shader: "Unlit/Texture"
   (No lighting needed for video)

4. Drag VideoMaterial onto VideoSphere in Hierarchy
```

### Step 5.5: Flip Sphere (View from Inside)
```
1. Project → Right-click → Create → Folder
   Name: "Scripts"

2. Scripts → Right-click → Create → C# Script
   Name: "InvertSphere"

3. Double-click "InvertSphere" to open

4. Replace ALL content with:
```

See `UnityScripts/InvertSphere.cs` for the script.

```
5. Save file (Ctrl+S / Cmd+S)
6. Unity will compile automatically
7. Drag "InvertSphere" script onto VideoSphere in Hierarchy
8. Script appears in Inspector under VideoSphere
```

---

## PHASE 6: Add Video Player System (30 minutes)

### Step 6.1: Create Video Player
```
1. Select VideoSphere in Hierarchy
2. Inspector → Add Component
3. Type "Video Player" → Select it
4. Video Player settings:
   - Source: "Video Clip" (we'll change to URL later)
   - Render Mode: "Material Override"
   - Target Material Renderer: Drag VideoSphere here
   - Material Property: "_MainTex"
   - Play On Awake: UNCHECK
   - Loop: UNCHECK
   - Skip On Drop: CHECK
```

### Step 6.2: Import Test Video
```
1. Download short 360 test video:
   - YouTube 360 videos
   - Or: https://www.shutterstock.com/video/search/360
   - Format: MP4 (H.264)
   - Resolution: 2560×1440 or 3840×1920

2. In Unity Project:
   - Right-click Assets → Create → Folder
   - Name: "Videos"

3. Drag test video into Assets/Videos folder

4. Select VideoSphere in Hierarchy

5. Inspector → Video Player:
   - Video Clip: Drag video from Project panel

6. Click Play button (top center)
   - Video should play inside sphere
   - If not visible: Check Camera is at (0,0,0)

7. Stop playback (click Play again)
```

---

## PHASE 7: Implement Data Collection Scripts (2 hours)

**All scripts are in the `UnityScripts/` folder. Follow these steps:**

### Step 7.1: Copy Scripts to Unity
```
1. Copy all .cs files from UnityScripts/ folder
2. Paste into Unity Project → Assets → Scripts folder
3. Unity will compile automatically
```

### Step 7.2: Set Up Data Collection Manager
```
1. Hierarchy → Right-click → Create Empty
2. Name: "DataCollectionManager"

3. Select DataCollectionManager

4. Inspector → Add Component:
   - DataCollector
   - VideoManager

5. In DataCollector component:
   - VR Camera: Drag "Main Camera" from XR Origin
   - Video Player: Drag "VideoSphere" from Hierarchy
   - Participant ID: "P001" (change per participant)
   - Video ID: "test_video"
   - Record Data: ✓ (checked)

6. In VideoManager component:
   - Video Player: Drag "VideoSphere"
   - Data Collector: Drag "DataCollectionManager"

7. Save scene (Ctrl+S / Cmd+S)
```

---

## PHASE 8: Build and Deploy (30 minutes)

### Step 8.1: Connect Quest Pro
```
1. Put on Quest Pro
2. Settings → System → Developer
3. Enable "USB Connection Dialog"

4. Connect USB-C cable: Quest Pro → Computer

5. Quest Pro popup:
   - "Allow USB Debugging?"
   - Check "Always allow from this computer"
   - Tap "OK"

6. Verify connection:
   - Open Command Prompt/Terminal
   - Navigate to Unity Android SDK:
     Windows: C:\Program Files\Unity\Hub\Editor\2022.3.XX\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\
     Mac: /Applications/Unity/Hub/Editor/2022.3.XX/PlaybackEngines/AndroidPlayer/SDK/platform-tools/
   
   - Run: adb devices
   - Should see: 1WMHHXXXXXXXXX    device
   - ✅ Connected!
```

### Step 8.2: Build Settings
```
In Unity:

1. File → Build Settings
2. Platform: Android (with Unity icon)
3. Run Device: Quest Pro should appear
4. Click "Add Open Scenes"
5. Settings:
   - Texture Compression: ASTC
   - Build System: Gradle
   - Development Build: ✓ (check)
6. Click "Build And Run"
7. Save as: "VRDataCollector.apk"
8. Location: Create "Builds" folder
9. Wait 5-10 minutes
10. App installs and launches automatically
```

### Step 8.3: Test on Quest Pro
```
1. Put on Quest Pro
2. App launches automatically
3. Test video plays inside sphere
4. Move head around - video stays stable
5. Look around with eyes (without moving head)
6. Let play for 30 seconds
7. Take off headset
```

### Step 8.4: Retrieve Data
```
Method A: Using ADB

1. Command Prompt/Terminal
2. Navigate to ADB location (see Step 8.1)
3. Check data exists:
   adb shell ls /sdcard/Android/data/com.yourname.vrdatacolllector/files/DataCollection/

4. Copy files:
   adb pull /sdcard/Android/data/com.yourname.vrdatacollector/files/DataCollection/ ./QuestData/

5. Open CSV files to verify data

Method B: Using SideQuest (Easier)

1. Download: https://sidequestvr.com/
2. Install and open SideQuest
3. Connect Quest Pro (auto-detects)
4. Click file browser icon
5. Navigate to:
   /sdcard/Android/data/com.yourname.vrdatacollector/files/DataCollection/
6. Select CSV files → Right-click → Download
7. Save to computer
```

---

## PHASE 9: Prepare for Real Data Collection (1 hour)

### Step 9.1: Prepare Your Videos
```
1. Gather all 14 videos (or however many you have)
2. Ensure format:
   - Equirectangular projection
   - MP4 (H.264 codec)
   - Resolution: 2560×1440 or higher

3. Copy videos to Quest Pro:
   - Connect Quest Pro to computer
   - Copy videos to: /sdcard/Movies/VRStudy/
   
   Windows: Use File Explorer (Quest Pro appears as drive)
   Mac: Use Android File Transfer

4. In Unity VideoManager:
   - Add video URLs:
     file:///sdcard/Movies/VRStudy/video1.mp4
     file:///sdcard/Movies/VRStudy/video2.mp4
     ... etc.
   - Add video IDs:
     video_01
     video_02
     ... etc.
```

### Step 9.2: Create Participant Setup Scene
```
1. File → New Scene
2. Save as: "ParticipantSetup"

3. Add UI:
   - Hierarchy → UI → Canvas
   - Hierarchy → UI → Input Field
     Name: "ParticipantIDInput"
     Placeholder: "Enter Participant ID (e.g., P001)"
   - Hierarchy → UI → Button
     Text: "Start Data Collection"

4. Create script: ParticipantSetup.cs
   (See UnityScripts/ folder)

5. Attach script to Canvas
6. Wire button to script

7. Build Settings:
   - Add both scenes (ParticipantSetup first)
   - Rebuild app
```

---

## PHASE 10: Data Collection Checklist

### Before Each Session:
```
□ Quest Pro charged (>80%)
□ Lenses cleaned
□ Facial interface cleaned
□ Videos loaded on Quest Pro
□ Test run completed
□ Data from previous participant backed up
□ New folder ready for today's data
```

### During Session:
```
□ Consent form signed
□ Pre-study questionnaire completed
□ Participant ID assigned: P___
□ Measure IPD: ___ mm
□ Adjust IPD slider to measured value
□ Eye tracking calibrated
□ Calibration quality: Good/Excellent
□ Participant ID entered in app: P___
□ Start time: ___:___
□ All videos completed
□ End time: ___:___
```

### After Session:
```
□ Post-session questionnaire completed
□ Data retrieved from Quest Pro
□ Data backed up to computer
□ Data backed up to cloud/external drive
□ CSV files verified (opened and checked)
□ Quest Pro cleaned for next participant
```

---

## PHASE 11: Data Organization

### Folder Structure:
```
VR_Study_Data/
├── Raw_Data/
│   ├── P001/
│   │   ├── head_P001_video01_20240211_143022.csv
│   │   ├── eye_P001_video01_20240211_143022.csv
│   │   ├── combined_P001_video01_20240211_143022.csv
│   │   └── ... (all videos)
│   ├── P002/
│   └── ...
├── Questionnaires/
├── Video_Metadata/
└── Backups/
```

### Automated Backup Script:
See `backup_quest_data.sh` or `backup_quest_data.bat`

---

## Troubleshooting

### Unity Build Errors:
```
- Check Android SDK installed correctly
- Verify IL2CPP backend selected
- Check ARM64 checked, ARMv7 unchecked
- Try: File → Build Settings → Player Settings → Other Settings → Reset
```

### Eye Tracking Not Working:
```
- Verify eye tracking enabled in Quest Pro settings
- Recalibrate eye tracking
- Check Meta SDK version (should be 60+)
- Verify Quest Pro selected in XR settings
```

### Video Not Playing:
```
- Check video format (MP4 H.264)
- Verify video path correct
- Check video file size (not too large)
- Try lower resolution video first
```

### Data Not Saving:
```
- Check app has storage permissions
- Verify file path exists
- Check disk space on Quest Pro
- Look at Unity Console for errors
```

---

## Next Steps

1. ✅ Complete Unity setup
2. ✅ Test with one video
3. ✅ Verify data collection works
4. ✅ Prepare all videos
5. ✅ Run pilot study (yourself)
6. ✅ Collect data from participants
7. ✅ Process data for STAR-VP model

---

## Support Resources

- Meta Developer Docs: https://developer.oculus.com/documentation/
- Unity XR Docs: https://docs.unity3d.com/Manual/XR.html
- Quest Pro Eye Tracking: https://developer.oculus.com/documentation/unity/unity-isdk-eye-tracking/
- Unity Forum: https://forum.unity.com/

---

**Good luck with your data collection! 🚀**
