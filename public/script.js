const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const startBtn = document.getElementById("start");
    const captureBtn = document.getElementById("capture");
    const predictBtn = document.getElementById("predictBtn");
    const outputImg = document.getElementById("outputImg");
    const loader = document.getElementById("loader");

    startBtn.onclick = async () => {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
    };

    captureBtn.onclick = async () => {
      const context = canvas.getContext("2d");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataURL = canvas.toDataURL("image/png");

      const res = await fetch("/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: dataURL }),
      });

      const data = await res.json();
      alert(data.message || "Image uploaded!");
    };

    predictBtn.onclick = async () => {
      predictBtn.disabled = true;
      loader.style.display = "block";

      const res = await fetch("/predict", { method: "POST" });
      const data = await res.json();

      loader.style.display = "none";
      predictBtn.disabled = false;

      if (data.success) {
        outputImg.src = data.predictedImage;
        outputImg.style.display = "block";
      } else {
        alert("Prediction failed.");
      }
    };