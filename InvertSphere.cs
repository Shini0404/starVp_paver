using UnityEngine;

/// <summary>
/// Flips the sphere mesh so it can be viewed from inside (for 360 video)
/// </summary>
public class InvertSphere : MonoBehaviour
{
    void Start()
    {
        // Get the mesh filter component
        MeshFilter meshFilter = GetComponent<MeshFilter>();
        if (meshFilter == null)
        {
            Debug.LogError("InvertSphere: No MeshFilter found!");
            return;
        }

        Mesh mesh = meshFilter.mesh;

        // Reverse all triangles to flip normals
        int[] triangles = mesh.triangles;
        System.Array.Reverse(triangles);
        mesh.triangles = triangles;

        // Recalculate normals to point inward
        mesh.RecalculateNormals();

        Debug.Log("Sphere inverted successfully - ready for 360 video viewing");
    }
}
