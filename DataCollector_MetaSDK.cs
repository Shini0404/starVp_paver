using UnityEngine;
using UnityEngine.XR;
using UnityEngine.Video;
using System.Collections.Generic;
using System.IO;
using System;

/// <summary>
/// Alternative DataCollector using Meta SDK directly (OVRPlugin)
/// Use this version if the standard Unity XR Input doesn't work for eye tracking
/// 
/// IMPORTANT: This requires Oculus Integration package or Meta XR SDK
/// Add this to your project if eye tracking doesn't work with DataCollector.cs
/// </summary>
public class DataCollector_MetaSDK : MonoBehaviour
{
    [Header("References")]
    public Camera vrCamera;
    public VideoPlayer videoPlayer;

    [Header("Settings")]
    public string participantID = "P001";
    public string videoID = "video_01";
    public bool recordData = true;
    public float recordingRate = 90f; // Hz (Quest Pro native rate)

    [Header("File Paths")]
    private string basePath;
    private StreamWriter headTrackingFile;
    private StreamWriter eyeTrackingFile;
    private StreamWriter combinedFile;

    // Tracking data
    private float startTime;
    private int frameCount = 0;
    private float lastRecordTime = 0f;
    private float recordInterval;

    // Previous frame data for velocity calculation
    private Vector3 previousHeadRotation;
    private Vector3 previousGazeDirection;
    private float previousTime;

    // Eye tracking state (Meta SDK)
    private bool eyeTrackingAvailable = false;

    void Start()
    {
        // Set up file paths
        basePath = Application.persistentDataPath + "/DataCollection/";

        // Create directory if doesn't exist
        if (!Directory.Exists(basePath))
        {
            Directory.CreateDirectory(basePath);
        }

        Debug.Log("Data will be saved to: " + basePath);

        // Calculate recording interval
        recordInterval = 1f / recordingRate;

        // Initialize eye tracking
        InitializeEyeTracking();

        // Create CSV files
        CreateDataFiles();

        // Start recording
        startTime = Time.time;
        previousTime = startTime;
        previousHeadRotation = vrCamera.transform.eulerAngles;
        previousGazeDirection = Vector3.forward;

        // Start video playback
        if (videoPlayer != null && videoPlayer.clip != null)
        {
            videoPlayer.Play();
        }
    }

    void InitializeEyeTracking()
    {
        // Check if we're on Quest Pro
        #if UNITY_ANDROID && !UNITY_EDITOR
        // Try to use OVRPlugin (requires Meta SDK)
        try
        {
            // Check if Quest Pro
            var headsetType = OVRPlugin.GetSystemHeadsetType();
            eyeTrackingAvailable = (headsetType == OVRPlugin.SystemHeadsetType.Quest_Pro);
            
            if (eyeTrackingAvailable)
            {
                Debug.Log("Quest Pro detected. Eye tracking should be available.");
            }
            else
            {
                Debug.LogWarning($"Headset type: {headsetType}. Eye tracking may not be available.");
            }
        }
        catch (System.Exception e)
        {
            Debug.LogWarning($"Could not check headset type: {e.Message}");
            Debug.LogWarning("Make sure Meta XR SDK or Oculus Integration is installed.");
            eyeTrackingAvailable = false;
        }
        #else
        Debug.LogWarning("Eye tracking only works on Quest Pro device, not in editor.");
        eyeTrackingAvailable = false;
        #endif
    }

    void CreateDataFiles()
    {
        string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");

        // Head tracking file
        string headFile = basePath + $"head_{participantID}_{videoID}_{timestamp}.csv";
        headTrackingFile = new StreamWriter(headFile);
        headTrackingFile.WriteLine("Timestamp,PlaybackTime,UnitQuaternion.x,UnitQuaternion.y,UnitQuaternion.z,UnitQuaternion.w,HmdPosition.x,HmdPosition.y,HmdPosition.z,FrameNumber,Yaw,Pitch,Roll,YawVelocity,PitchVelocity,RollVelocity");

        // Eye tracking file
        string eyeFile = basePath + $"eye_{participantID}_{videoID}_{timestamp}.csv";
        eyeTrackingFile = new StreamWriter(eyeFile);
        eyeTrackingFile.WriteLine("Timestamp,PlaybackTime,FrameNumber,GazeDirection.x,GazeDirection.y,GazeDirection.z,GazeYaw,GazePitch,LeftPupilDiameter,RightPupilDiameter,LeftEyeOpenness,RightEyeOpenness,LeftEyeConfidence,RightEyeConfidence,IsFixating,IsSaccade,FixationDuration,AveragePupilDiameter,TrackingQuality");

        // Combined file
        string combinedFilePath = basePath + $"combined_{participantID}_{videoID}_{timestamp}.csv";
        combinedFile = new StreamWriter(combinedFilePath);
        combinedFile.WriteLine("Timestamp,PlaybackTime,FrameNumber,HeadYaw,HeadPitch,HeadRoll,GazeYaw,GazePitch,GazeRelativeHorizontal,GazeRelativeVertical,PupilAverage,EyeHeadOffsetAngle,EyeLeading,HeadFollowing,Aligned");
    }

    void Update()
    {
        if (!recordData) return;

        float currentTime = Time.time - startTime;

        // Record at specified rate (90 Hz for Quest Pro)
        if (currentTime - lastRecordTime < recordInterval)
        {
            return;
        }

        lastRecordTime = currentTime;
        frameCount++;

        // Get video playback time
        float playbackTime = videoPlayer != null && videoPlayer.isPlaying ? (float)videoPlayer.time : 0f;

        // Collect head tracking
        Vector3 headPos = vrCamera.transform.position;
        Quaternion headRot = vrCamera.transform.rotation;

        // Convert rotation to Euler angles
        Vector3 headEuler = headRot.eulerAngles;
        float headYaw = NormalizeAngle(headEuler.y);
        float headPitch = NormalizeAngle(headEuler.x);
        float headRoll = NormalizeAngle(headEuler.z);

        // Calculate velocities
        float deltaTime = currentTime - previousTime;
        if (deltaTime > 0)
        {
            Vector3 velocity = (new Vector3(headYaw, headPitch, headRoll) - previousHeadRotation) / deltaTime;

            // Write head tracking
            headTrackingFile.WriteLine($"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff},{playbackTime:F3}," +
                $"{headRot.x:F6},{headRot.y:F6},{headRot.z:F6},{headRot.w:F6}," +
                $"{headPos.x:F6},{headPos.y:F6},{headPos.z:F6}," +
                $"{frameCount},{headYaw:F4},{headPitch:F4},{headRoll:F4}," +
                $"{velocity.x:F4},{velocity.y:F4},{velocity.z:F4}");
        }

        // Collect eye tracking using Meta SDK
        bool hasEyeData = TryGetEyeTrackingData_MetaSDK(
            out Vector3 gazeDirection,
            out float leftPupil,
            out float rightPupil,
            out float leftOpenness,
            out float rightOpenness,
            out float leftConfidence,
            out float rightConfidence,
            out bool isFixating,
            out bool isSaccade,
            out float fixationDuration
        );

        if (hasEyeData)
        {
            // Convert gaze to spherical coordinates
            float gazeYaw = Mathf.Atan2(gazeDirection.x, gazeDirection.z) * Mathf.Rad2Deg;
            float gazePitch = Mathf.Asin(gazeDirection.y) * Mathf.Rad2Deg;

            // Calculate relative gaze (gaze - head)
            float relativeH = NormalizeAngle(gazeYaw - headYaw);
            float relativeV = NormalizeAngle(gazePitch - headPitch);

            float avgPupil = (leftPupil + rightPupil) / 2f;
            float eyeHeadOffset = Mathf.Sqrt(relativeH * relativeH + relativeV * relativeV);

            // Detect eye leading
            bool eyeLeading = Mathf.Abs(relativeH) > 5f || Mathf.Abs(relativeV) > 5f;
            Vector3 velocity = (new Vector3(headYaw, headPitch, headRoll) - previousHeadRotation) / deltaTime;
            bool headFollowing = eyeLeading && (Mathf.Abs(velocity.x) > 10f || Mathf.Abs(velocity.y) > 10f);
            bool aligned = eyeHeadOffset < 10f;

            // Calculate tracking quality
            float trackingQuality = (leftConfidence + rightConfidence) / 2f;

            // Write eye tracking
            eyeTrackingFile.WriteLine($"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff},{playbackTime:F3},{frameCount}," +
                $"{gazeDirection.x:F6},{gazeDirection.y:F6},{gazeDirection.z:F6}," +
                $"{gazeYaw:F4},{gazePitch:F4}," +
                $"{leftPupil:F4},{rightPupil:F4}," +
                $"{leftOpenness:F4},{rightOpenness:F4}," +
                $"{leftConfidence:F4},{rightConfidence:F4}," +
                $"{(isFixating ? 1 : 0)},{(isSaccade ? 1 : 0)},{fixationDuration:F4}," +
                $"{avgPupil:F4},{trackingQuality:F4}");

            // Write combined
            combinedFile.WriteLine($"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff},{playbackTime:F3},{frameCount}," +
                $"{headYaw:F4},{headPitch:F4},{headRoll:F4}," +
                $"{gazeYaw:F4},{gazePitch:F4}," +
                $"{relativeH:F4},{relativeV:F4}," +
                $"{avgPupil:F4},{eyeHeadOffset:F4}," +
                $"{(eyeLeading ? 1 : 0)},{(headFollowing ? 1 : 0)},{(aligned ? 1 : 0)}");

            previousGazeDirection = gazeDirection;
        }

        // Update previous frame data
        previousHeadRotation = new Vector3(headYaw, headPitch, headRoll);
        previousTime = currentTime;

        // Check if video ended
        if (videoPlayer != null && !videoPlayer.isPlaying && videoPlayer.time >= videoPlayer.length - 0.1f)
        {
            StopRecording();
        }
    }

    bool TryGetEyeTrackingData_MetaSDK(
        out Vector3 gazeDirection,
        out float leftPupil,
        out float rightPupil,
        out float leftOpenness,
        out float rightOpenness,
        out float leftConfidence,
        out float rightConfidence,
        out bool isFixating,
        out bool isSaccade,
        out float fixationDuration)
    {
        gazeDirection = Vector3.forward;
        leftPupil = 0f;
        rightPupil = 0f;
        leftOpenness = 1f;
        rightOpenness = 1f;
        leftConfidence = 0f;
        rightConfidence = 0f;
        isFixating = false;
        isSaccade = false;
        fixationDuration = 0f;

        #if UNITY_ANDROID && !UNITY_EDITOR
        if (!eyeTrackingAvailable)
        {
            return false;
        }

        try
        {
            // Use OVRPlugin to get eye tracking data
            OVRPlugin.EyeGazesState eyeGazesState = new OVRPlugin.EyeGazesState();
            bool success = OVRPlugin.GetEyeGazesState(OVRPlugin.Step.Render, -1, ref eyeGazesState);

            if (!success)
            {
                return false;
            }

            Vector3 leftGaze = Vector3.zero;
            Vector3 rightGaze = Vector3.zero;
            bool leftValid = false;
            bool rightValid = false;

            // Left eye
            if (eyeGazesState.IsValid[0])
            {
                OVRPlugin.EyeGazeState leftEye = eyeGazesState.EyeGazes[0];
                Quaternion leftRot = new Quaternion(
                    leftEye.Pose.Orientation.x,
                    leftEye.Pose.Orientation.y,
                    leftEye.Pose.Orientation.z,
                    leftEye.Pose.Orientation.w
                );
                leftGaze = leftRot * Vector3.forward;
                leftPupil = leftEye.PupilDiameter * 1000f; // Convert to mm
                leftConfidence = leftEye.IsValid ? 1f : 0f;
                leftValid = true;
            }

            // Right eye
            if (eyeGazesState.IsValid[1])
            {
                OVRPlugin.EyeGazeState rightEye = eyeGazesState.EyeGazes[1];
                Quaternion rightRot = new Quaternion(
                    rightEye.Pose.Orientation.x,
                    rightEye.Pose.Orientation.y,
                    rightEye.Pose.Orientation.z,
                    rightEye.Pose.Orientation.w
                );
                rightGaze = rightRot * Vector3.forward;
                rightPupil = rightEye.PupilDiameter * 1000f; // Convert to mm
                rightConfidence = rightEye.IsValid ? 1f : 0f;
                rightValid = true;
            }

            if (leftValid && rightValid)
            {
                gazeDirection = ((leftGaze + rightGaze) / 2f).normalized;
            }
            else if (leftValid)
            {
                gazeDirection = leftGaze;
            }
            else if (rightValid)
            {
                gazeDirection = rightGaze;
            }
            else
            {
                return false;
            }

            // Fixation/saccade detection
            float deltaTime = Time.deltaTime;
            if (deltaTime > 0)
            {
                float gazeVelocity = Vector3.Distance(gazeDirection, previousGazeDirection) / deltaTime;
                isSaccade = gazeVelocity > 100f;
                isFixating = !isSaccade && gazeVelocity < 30f;
                fixationDuration = isFixating ? deltaTime : 0f;
            }

            return true;
        }
        catch (System.Exception e)
        {
            Debug.LogWarning($"Error getting eye tracking data: {e.Message}");
            return false;
        }
        #else
        // Not on device - return false
        return false;
        #endif
    }

    float NormalizeAngle(float angle)
    {
        while (angle > 180f) angle -= 360f;
        while (angle < -180f) angle += 360f;
        return angle;
    }

    void StopRecording()
    {
        Debug.Log("Recording stopped. Video ended.");

        // Close files
        if (headTrackingFile != null)
        {
            headTrackingFile.Flush();
            headTrackingFile.Close();
        }
        if (eyeTrackingFile != null)
        {
            eyeTrackingFile.Flush();
            eyeTrackingFile.Close();
        }
        if (combinedFile != null)
        {
            combinedFile.Flush();
            combinedFile.Close();
        }

        recordData = false;

        Debug.Log($"Data saved to: {basePath}");
    }

    void OnApplicationQuit()
    {
        StopRecording();
    }

    void OnDestroy()
    {
        StopRecording();
    }
}
