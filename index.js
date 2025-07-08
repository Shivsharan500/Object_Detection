const express = require("express");
const app = express();
if (process.env.NODE_ENV !== "production") {
  require("dotenv").config();
}
const port = process.env.port || 3000;
const path = require("path");
const fs = require("fs");
const { google } = require("googleapis");
const bodyParser = require("body-parser");
const { exec } = require("child_process");


app.set("view engine","ejs");
app.set("views",path.join(__dirname,"views"));
app.use(express.static(path.join(__dirname,"public")));
app.use(express.urlencoded({extended:true}));
app.use(bodyParser.json({ limit: "10mb" }));

const auth = new google.auth.GoogleAuth({
  keyFile: process.env.GOOGLE_APPLICATION_CREDENTIALS || "credentials.json",
  scopes: ["https://www.googleapis.com/auth/drive.file"],
});
const drive = google.drive({ version: "v3", auth });

const FOLDER_ID = process.env.INPUT_FOLDER_ID;

app.post("/upload" , async (req,res) => {
    try {
    const base64Data = req.body.image.replace(/^data:image\/png;base64,/, "");
    const filePath = "capture.png";

    fs.writeFileSync(filePath, base64Data, "base64");

    const fileMetadata = {
      name: `capture_${Date.now()}.png`,
      parents: [FOLDER_ID],
    };
    const media = {
      mimeType: "image/png",
      body: fs.createReadStream(filePath),
    };

    

    const driveRes = await drive.files.create({
      resource: fileMetadata,
      media: media,
      fields: "id",
    });

    // Optional: delete the local file after upload
    fs.unlinkSync(filePath);

    res.json({ message: "Uploaded to Drive!", fileId: driveRes.data.id });
  } catch (err) {
    console.error(err);
    res.status(500).send("Upload failed");
  }
    
});

app.post("/predict" , (req,res) => {
    console.log("Running prediction body");
    exec("python drive_yolo_predict.py", (error, stdout2, stderr2) => {
      if (error) {
        console.error("Python script failed:", error);
        console.error("stderr:", stderr2);
        return res.status(500).json({ success: false, message: "Prediction failed" });
      }

      console.log("STDOUT:", stdout2);

      try {
        const base64 = fs.readFileSync("result_base64.txt", "utf8");
        fs.unlinkSync("result_base64.txt");
        res.json({ success: true, predictedImage: base64 });
      } catch (e) {
        console.error("Could not read result_base64.txt:", e);
        res.status(500).json({ success: false, message: "No result generated" });
      }
    });
});


app.get("/", (req,res) => {
    res.render("home.ejs");
});

app.listen(port, () => {
    console.log(`Server is Listening to port:${port}`);
});