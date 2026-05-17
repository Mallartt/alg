package com.example.sleepdetector

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.facelandmarker.FaceLandmarker
import com.google.mediapipe.tasks.vision.facelandmarker.FaceLandmarkerResult
import java.io.File
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {

    private lateinit var viewFinder: PreviewView
    private lateinit var overlayView: OverlayView
    private lateinit var tvStatus: TextView

    private lateinit var cameraExecutor: ExecutorService
    private var faceLandmarker: FaceLandmarker? = null

    // =======================
    // 📊 ЛОГИ ДЛЯ ГРАФИКОВ
    // =======================
    private val timestamps = mutableListOf<Long>()
    private val occlusionScores = mutableListOf<Int>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        viewFinder = findViewById(R.id.viewFinder)
        overlayView = findViewById(R.id.overlayView)
        tvStatus = findViewById(R.id.tvStatus)

        tvStatus.text = "Шаг 1: Проверка разрешений..."
        tvStatus.setTextColor(Color.YELLOW)

        cameraExecutor = Executors.newSingleThreadExecutor()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED
        ) {
            setupMediaPipe()
            startCamera()
        } else {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CAMERA), 10)
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        if (requestCode == 10 && grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            setupMediaPipe()
            startCamera()
        } else {
            tvStatus.text = "❌ Нет разрешения на камеру!"
        }
    }

    private fun setupMediaPipe() {
        try {
            val fileList = assets.list("")
            val hasModel = fileList?.contains("face_landmarker.task") == true

            if (!hasModel) {
                tvStatus.text = "❌ Нет модели в assets"
                return
            }

            val baseOptions = BaseOptions.builder()
                .setModelAssetPath("face_landmarker.task")
                .build()

            val options = FaceLandmarker.FaceLandmarkerOptions.builder()
                .setBaseOptions(baseOptions)
                .setRunningMode(RunningMode.LIVE_STREAM)
                .setResultListener(this::onFaceResult)
                .setErrorListener { error ->
                    Log.e("MediaPipe", error.message ?: "error")
                }
                .build()

            faceLandmarker = FaceLandmarker.createFromOptions(this, options)

            tvStatus.text = "✅ Модель загружена"

        } catch (e: Exception) {
            tvStatus.text = "❌ Ошибка: ${e.message}"
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(viewFinder.surfaceProvider)
            }

            val imageAnalyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                .build()

            imageAnalyzer.setAnalyzer(cameraExecutor) { imageProxy ->
                processImage(imageProxy)
            }

            val cameraSelector = CameraSelector.DEFAULT_FRONT_CAMERA

            cameraProvider.unbindAll()
            cameraProvider.bindToLifecycle(
                this,
                cameraSelector,
                preview,
                imageAnalyzer
            )

        }, ContextCompat.getMainExecutor(this))
    }

    private fun processImage(imageProxy: ImageProxy) {
        val bitmap = imageProxy.toBitmap()
        val mpImage = BitmapImageBuilder(bitmap).build()
        val frameTime = SystemClock.uptimeMillis()

        faceLandmarker?.detectAsync(mpImage, frameTime)

        imageProxy.close()
    }

    private fun onFaceResult(
        result: FaceLandmarkerResult,
        mpImage: com.google.mediapipe.framework.image.MPImage
    ) {
        if (result.faceLandmarks().isEmpty()) {
            runOnUiThread {
                tvStatus.text = "👤 Лицо не найдено"
                overlayView.clearOcclusionMap()
            }
            return
        }

        val landmarks = result.faceLandmarks()[0]

        val leftEye = listOf(33, 133, 157, 158)
        val rightEye = listOf(263, 362, 387, 386)
        val nose = listOf(1, 2, 3, 4)
        val mouth = listOf(61, 291, 0, 17)

        fun occluded(indices: List<Int>): Boolean {
            for (i in indices) {
                val p = landmarks[i]
                if (p.x() == 0.0f && p.y() == 0.0f) return true
            }
            return false
        }

        val l = occluded(leftEye)
        val r = occluded(rightEye)
        val n = occluded(nose)
        val m = occluded(mouth)

        // =======================
        // 📊 ЛОГИРОВАНИЕ ДАННЫХ
        // =======================
        val now = SystemClock.uptimeMillis()

        val score = listOf(l, r, n, m).count { it }

        timestamps.add(now)
        occlusionScores.add(score)

        overlayView.updateOcclusionRegions(l, r, n, m, landmarks)

        runOnUiThread {
            val parts = mutableListOf<String>()
            if (l) parts.add("Левый глаз")
            if (r) parts.add("Правый глаз")
            if (n) parts.add("Нос")
            if (m) parts.add("Рот")

            if (parts.isEmpty()) {
                tvStatus.text = "✅ Лицо открыто"
                tvStatus.setTextColor(Color.GREEN)
            } else {
                tvStatus.text = "⚠️ Окклюзия: ${parts.joinToString()}"
                tvStatus.setTextColor(Color.RED)
            }
        }
    }

    // =======================
    // 💾 СОХРАНЕНИЕ CSV
    // =======================
    private fun saveCsv() {
        try {
            val file = File(getExternalFilesDir(null), "occlusion_log.csv")

            file.printWriter().use { out ->
                out.println("time,score")

                for (i in timestamps.indices) {
                    out.println("${timestamps[i]},${occlusionScores[i]}")
                }
            }

            Toast.makeText(this, "CSV saved: ${file.path}", Toast.LENGTH_LONG).show()

        } catch (e: Exception) {
            Log.e("CSV", "Error saving file", e)
        }
    }

    override fun onDestroy() {
        super.onDestroy()

        saveCsv()

        cameraExecutor.shutdown()
        faceLandmarker?.close()
    }
}