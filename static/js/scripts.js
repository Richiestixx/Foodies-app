document.addEventListener("DOMContentLoaded", function () {
  // Image input and preview elements
  const imageInput = document.getElementById("image-input");
  const previewImage = document.getElementById("preview-image");

  // Listen for file input change event
  imageInput.addEventListener("change", function (event) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = function (e) {
        previewImage.src = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  });

  // Listen for submit button click event
  const submitPhoto = document.getElementById("submit-photo");
  submitPhoto.addEventListener("click", function (event) {
    event.preventDefault();
    if (!previewImage.src) {
      alert("Please select a photo to submit.");
      return;
    }

    // Submit the photo to your server
    // You can send the image data as a base64 string or use FormData to send the file itself
    // Implement the logic to send the photo to the server
    console.log("Submitting photo:", previewImage.src);
  });
});
