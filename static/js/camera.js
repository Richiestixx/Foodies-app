document.getElementById('image-input').addEventListener('change', function (event) {
    const file = event.target.files[0];
    const reader = new FileReader();

    reader.onloadend = function () {
        document.getElementById('selected-image').src = reader.result;
    }

    if (file) {
        reader.readAsDataURL(file);
    }
});

document.getElementById('selected-image').addEventListener('click', function () {
    document.getElementById('image-input').click();
});

// Add event listeners for gallery images and camera icon here

async function submitPhoto() {
  const imageFile = document.getElementById("image-input").files[0];
  if (!imageFile) {
    alert("Please select an image to upload");
    return;
  }

  const formData = new FormData();
  formData.append("image", imageFile);

  const response = await fetch("/submit_photo", {
    method: "POST",
    body: formData,
  });

  const result = await response.json();

  if (result.success) {
    alert("Image uploaded successfully");
    // Redirect to another page or show a success message
  } else {
    alert("Error uploading image");
  }
}
