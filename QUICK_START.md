# Quick Start Guide: Quest Pro Data Collection

## ⚠️ Key Decision: Unity Version

**RECOMMENDATION: Use Unity 2022.3 LTS** (NOT 2021 LTS)

### Why Unity 2022.3 LTS?
- ✅ Better Quest Pro eye tracking support
- ✅ More stable Meta XR SDK integration  
- ✅ Better performance with 360° video
- ✅ Still LTS (stable and supported)

### Why NOT Unity 2021 LTS?
- ❌ Older eye tracking API (may not work well with Quest Pro)
- ❌ Compatibility issues with newer Meta SDK versions
- ❌ Missing Quest Pro specific optimizations

### Why NOT Latest Unity?
- ❌ Too new - may have bugs
- ❌ Less tested with Quest Pro
- ❌ May have breaking changes

---

## What You Have Now

### 1. Complete Setup Guide
📄 `QUEST_PRO_DATA_COLLECTION.md` - Full step-by-step guide

### 2. Unity Scripts
📁 `UnityScripts/` folder contains:
- `InvertSphere.cs` - Flips sphere for 360 video viewing
- `DataCollector.cs` - Main data collection (Unity XR Input)
- `DataCollector_MetaSDK.cs` - Alternative using Meta SDK directly
- `VideoManager.cs` - Manages video playlist
- `ParticipantSetup.cs` - UI for participant ID entry

### 3. Backup Scripts
- `backup_quest_data.sh` - Linux/Mac backup script
- `backup_quest_data.bat` - Windows backup script

---

## Quick Setup Steps

### Step 1: Install Unity 2022.3 LTS
```
1. Download Unity Hub
2. Install Unity 2022.3.x LTS
3. Install Android Build Support modules
```

### Step 2: Create Unity Project
```
1. New Project → 3D Core
2. Switch to Android platform
3. Configure Android settings (see guide)
```

### Step 3: Install Meta XR SDK
```
Window → Package Manager → Add package from git URL
Enter: com.meta.xr.sdk.all
```

### Step 4: Copy Scripts
```
Copy all .cs files from UnityScripts/ folder
Paste into Unity project: Assets/Scripts/
```

### Step 5: Set Up Scene
```
1. Add XR Origin (Action-based)
2. Add Sphere → Name: VideoSphere
3. Add Empty GameObject → Name: DataCollectionManager
4. Attach scripts (see guide)
```

### Step 6: Build and Test
```
1. Connect Quest Pro
2. Build and Run
3. Test with one video
4. Verify data files created
```

---

## Eye Tracking: Two Options

### Option 1: Unity XR Input (Try First)
- Use `DataCollector.cs`
- Uses Unity's standard XR Input system
- May work, but might not have full Quest Pro features

### Option 2: Meta SDK Direct (If Option 1 Fails)
- Use `DataCollector_MetaSDK.cs`
- Requires OVRPlugin (from Meta SDK)
- Full Quest Pro eye tracking access
- See `UnityScripts/EyeTrackingNote.md` for details

**If eye tracking doesn't work with Option 1, switch to Option 2.**

---

## Data Collection Checklist

### Before Each Session:
- [ ] Quest Pro charged (>80%)
- [ ] Lenses cleaned
- [ ] Videos loaded on Quest Pro
- [ ] Test run completed
- [ ] Previous data backed up

### During Session:
- [ ] Participant ID entered
- [ ] IPD adjusted
- [ ] Eye tracking calibrated
- [ ] All videos completed

### After Session:
- [ ] Data retrieved from Quest Pro
- [ ] Data backed up
- [ ] CSV files verified

---

## Data Output

### Files Created Per Video:
1. `head_[participantID]_[videoID]_[timestamp].csv` - Head tracking
2. `eye_[participantID]_[videoID]_[timestamp].csv` - Eye tracking  
3. `combined_[participantID]_[videoID]_[timestamp].csv` - Combined metrics

### Data Location:
```
Quest Pro: /sdcard/Android/data/com.yourname.vrdatacollector/files/DataCollection/
```

### Retrieve Data:
```bash
# Using ADB
adb pull /sdcard/Android/data/com.yourname.vrdatacollector/files/DataCollection/ ./QuestData/

# Or use backup script
./backup_quest_data.sh
```

---

## Troubleshooting

### Eye Tracking Not Working?
1. Check Quest Pro settings: Eye Tracking ON
2. Recalibrate eye tracking
3. Try `DataCollector_MetaSDK.cs` instead
4. Check Meta SDK version (should be 60+)

### Videos Not Playing?
1. Check video format: MP4 (H.264)
2. Verify file path is correct
3. Try lower resolution video first

### Build Errors?
1. Check Android SDK installed
2. Verify IL2CPP backend selected
3. Check ARM64 checked, ARMv7 unchecked

### Data Not Saving?
1. Check app has storage permissions
2. Verify disk space on Quest Pro
3. Check Unity Console for errors

---

## Next Steps

1. ✅ Read `QUEST_PRO_DATA_COLLECTION.md` for full details
2. ✅ Set up Unity 2022.3 LTS
3. ✅ Create project and copy scripts
4. ✅ Test with one video
5. ✅ Verify data collection works
6. ✅ Prepare all videos
7. ✅ Run pilot study
8. ✅ Collect data from participants

---

## Support

- Full Guide: `QUEST_PRO_DATA_COLLECTION.md`
- Scripts Documentation: `UnityScripts/README.md`
- Eye Tracking Notes: `UnityScripts/EyeTrackingNote.md`
- Meta Developer Docs: https://developer.oculus.com/documentation/
- Unity XR Docs: https://docs.unity3d.com/Manual/XR.html

---

**Good luck with your data collection! 🚀**
