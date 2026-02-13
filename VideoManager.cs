using UnityEngine;
using UnityEngine.Video;
using System.Collections.Generic;
using System.IO;

/// <summary>
/// Manages video playlist and playback for data collection
/// Supports both local files and URLs
/// </summary>
public class VideoManager : MonoBehaviour
{
    [Header("References")]
    public VideoPlayer videoPlayer;
    public DataCollector dataCollector;

    [Header("Video Configuration")]
    [Tooltip("List of video file paths or URLs")]
    public List<string> videoURLs = new List<string>();
    
    [Tooltip("List of video IDs (must match videoURLs count)")]
    public List<string> videoIDs = new List<string>();

    [Header("Settings")]
    [Tooltip("Delay between videos (seconds)")]
    public float delayBetweenVideos = 2f;
    
    [Tooltip("Auto-play next video when current ends")]
    public bool autoPlayNext = true;

    private int currentVideoIndex = 0;
    private bool isPreparing = false;
    private bool allVideosCompleted = false;

    void Start()
    {
        // Validate setup
        if (videoPlayer == null)
        {
            Debug.LogError("VideoManager: VideoPlayer not assigned!");
            return;
        }

        if (dataCollector == null)
        {
            Debug.LogWarning("VideoManager: DataCollector not assigned. Data won't be linked to videos.");
        }

        // Set up video player callbacks
        videoPlayer.prepareCompleted += OnVideoPrepared;
        videoPlayer.loopPointReached += OnVideoEnded;

        // Load first video if available
        if (videoURLs.Count > 0)
        {
            LoadVideo(0);
        }
        else
        {
            Debug.LogWarning("VideoManager: No videos configured. Add video URLs in Inspector.");
        }
    }

    void Update()
    {
        // Check if video finished (backup check)
        if (!isPreparing && videoPlayer != null && !videoPlayer.isPlaying && 
            videoPlayer.time >= videoPlayer.length - 0.5f && videoPlayer.length > 0)
        {
            if (autoPlayNext && !allVideosCompleted)
            {
                OnVideoEnded(videoPlayer);
            }
        }
    }

    public void LoadVideo(int index)
    {
        if (index < 0 || index >= videoURLs.Count)
        {
            Debug.LogWarning($"VideoManager: Invalid video index {index}. Total videos: {videoURLs.Count}");
            return;
        }

        if (videoIDs.Count != videoURLs.Count)
        {
            Debug.LogError($"VideoManager: videoIDs count ({videoIDs.Count}) doesn't match videoURLs count ({videoURLs.Count})!");
            return;
        }

        currentVideoIndex = index;
        isPreparing = true;

        string videoPath = videoURLs[index];
        string videoID = videoIDs[index];

        Debug.Log($"Loading video {index + 1}/{videoURLs.Count}: {videoID}");

        // Update data collector
        if (dataCollector != null)
        {
            dataCollector.videoID = videoID;
            dataCollector.recordData = true; // Ensure recording is on
        }

        // Check if it's a URL or local file
        if (videoPath.StartsWith("http://") || videoPath.StartsWith("https://"))
        {
            // URL - stream from web
            videoPlayer.source = VideoSource.Url;
            videoPlayer.url = videoPath;
        }
        else if (videoPath.StartsWith("file://"))
        {
            // Local file path
            videoPlayer.source = VideoSource.Url;
            videoPlayer.url = videoPath;
        }
        else
        {
            // Try as VideoClip (if video is in Unity project)
            videoPlayer.source = VideoSource.VideoClip;
            // Note: You'd need to assign VideoClip in Inspector for this to work
            Debug.LogWarning($"VideoManager: Path '{videoPath}' not recognized as URL. Using VideoClip source.");
        }

        // Prepare video
        videoPlayer.Prepare();
    }

    void OnVideoPrepared(VideoPlayer vp)
    {
        isPreparing = false;
        Debug.Log($"Video {currentVideoIndex + 1} prepared. Duration: {vp.length:F2}s. Playing...");
        vp.Play();
    }

    void OnVideoEnded(VideoPlayer vp)
    {
        Debug.Log($"Video {currentVideoIndex + 1} ended.");

        // Stop data collection for this video
        if (dataCollector != null)
        {
            // DataCollector will handle stopping when video ends
        }

        // Wait before loading next video
        if (autoPlayNext)
        {
            Invoke(nameof(LoadNextVideo), delayBetweenVideos);
        }
    }

    void LoadNextVideo()
    {
        currentVideoIndex++;

        if (currentVideoIndex < videoURLs.Count)
        {
            LoadVideo(currentVideoIndex);
        }
        else
        {
            allVideosCompleted = true;
            Debug.Log("All videos completed!");
            
            // Stop data collection
            if (dataCollector != null)
            {
                dataCollector.recordData = false;
            }
        }
    }

    public void PlayPause()
    {
        if (videoPlayer.isPlaying)
        {
            videoPlayer.Pause();
        }
        else
        {
            videoPlayer.Play();
        }
    }

    public void SkipToNext()
    {
        if (currentVideoIndex < videoURLs.Count - 1)
        {
            videoPlayer.Stop();
            LoadNextVideo();
        }
    }

    public void SkipToPrevious()
    {
        if (currentVideoIndex > 0)
        {
            videoPlayer.Stop();
            LoadVideo(currentVideoIndex - 1);
        }
    }

    void OnDestroy()
    {
        if (videoPlayer != null)
        {
            videoPlayer.prepareCompleted -= OnVideoPrepared;
            videoPlayer.loopPointReached -= OnVideoEnded;
        }
    }
}
