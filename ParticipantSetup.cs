using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;

/// <summary>
/// Simple UI for entering participant ID before starting data collection
/// </summary>
public class ParticipantSetup : MonoBehaviour
{
    [Header("UI References")]
    public InputField participantIDInput;
    public Button startButton;
    public Text statusText;

    [Header("Settings")]
    public string dataCollectionSceneName = "DataCollection";

    void Start()
    {
        // Auto-find UI elements if not assigned
        if (participantIDInput == null)
        {
            participantIDInput = FindObjectOfType<InputField>();
        }

        if (startButton == null)
        {
            startButton = FindObjectOfType<Button>();
        }

        // Set up button click
        if (startButton != null)
        {
            startButton.onClick.AddListener(StartCollection);
        }

        // Set placeholder text
        if (participantIDInput != null && participantIDInput.placeholder != null)
        {
            Text placeholder = participantIDInput.placeholder.GetComponent<Text>();
            if (placeholder != null)
            {
                placeholder.text = "Enter Participant ID (e.g., P001)";
            }
        }

        // Focus on input field
        if (participantIDInput != null)
        {
            participantIDInput.Select();
            participantIDInput.ActivateInputField();
        }

        UpdateStatus("Enter Participant ID and click Start");
    }

    public void StartCollection()
    {
        string participantID = participantIDInput != null ? participantIDInput.text.Trim() : "";

        if (string.IsNullOrEmpty(participantID))
        {
            UpdateStatus("Error: Please enter a Participant ID!");
            return;
        }

        // Validate participant ID format (optional)
        if (participantID.Length < 2)
        {
            UpdateStatus("Error: Participant ID should be at least 2 characters!");
            return;
        }

        // Save participant ID to PlayerPrefs (persists across scenes)
        PlayerPrefs.SetString("ParticipantID", participantID);
        PlayerPrefs.Save();

        Debug.Log($"Starting data collection for participant: {participantID}");

        UpdateStatus($"Loading data collection scene for {participantID}...");

        // Load data collection scene
        if (!string.IsNullOrEmpty(dataCollectionSceneName))
        {
            SceneManager.LoadScene(dataCollectionSceneName);
        }
        else
        {
            Debug.LogError("ParticipantSetup: Data collection scene name not set!");
            UpdateStatus("Error: Scene name not configured!");
        }
    }

    void UpdateStatus(string message)
    {
        if (statusText != null)
        {
            statusText.text = message;
        }
        Debug.Log($"ParticipantSetup: {message}");
    }

    void Update()
    {
        // Allow Enter key to start
        if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter))
        {
            StartCollection();
        }
    }
}
