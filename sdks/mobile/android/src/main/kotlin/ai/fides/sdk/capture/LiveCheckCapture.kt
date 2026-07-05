package ai.fides.sdk.capture

import android.content.Context
import android.os.Handler
import android.os.Looper
import androidx.camera.core.CameraSelector
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.FileOutputOptions
import androidx.camera.video.Quality
import androidx.camera.video.QualitySelector
import androidx.camera.video.Recorder
import androidx.camera.video.Recording
import androidx.camera.video.VideoCapture
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import java.io.File
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * CameraX-based live identity check recorder (~10s front camera + mic).
 * Host app binds a [PreviewView], then calls [startRecording].
 */
class LiveCheckCapture(
    private val context: Context,
    private val lifecycleOwner: LifecycleOwner,
) {
    private val mainHandler = Handler(Looper.getMainLooper())
    private val cameraExecutor: ExecutorService = Executors.newSingleThreadExecutor()
    private var cameraProvider: ProcessCameraProvider? = null
    private var videoCapture: VideoCapture<Recorder>? = null
    private var activeRecording: Recording? = null
    private var outputFile: File? = null
    private var tickRunnable: Runnable? = null
    private val recordingInProgress = AtomicBoolean(false)
    private val stopRequested = AtomicBoolean(false)

    fun bindPreview(
        previewView: PreviewView,
        onReady: () -> Unit,
        onError: (String) -> Unit,
    ) {
        val future = ProcessCameraProvider.getInstance(context)
        future.addListener(
            {
                try {
                    val provider = future.get()
                    cameraProvider = provider
                    bindUseCases(provider, previewView)
                    onReady()
                } catch (error: Throwable) {
                    onError(error.message ?: "Camera binding failed.")
                }
            },
            ContextCompat.getMainExecutor(context),
        )
    }

    fun startRecording(
        config: LiveCheckCaptureConfig = LiveCheckCaptureConfig(),
        callback: LiveCheckCaptureCallback,
    ) {
        val capture = videoCapture
        if (capture == null) {
            callback.onFailure("Camera preview is not ready. Call bindPreview() first.")
            return
        }
        if (!recordingInProgress.compareAndSet(false, true)) {
            callback.onFailure("A live check recording is already in progress.")
            return
        }
        stopRequested.set(false)

        val targetFile = File(context.cacheDir, "fides-live-check-${System.currentTimeMillis()}.mp4")
        outputFile = targetFile
        val outputOptions = FileOutputOptions.Builder(targetFile).build()

        callback.onRecordingStarted(config.durationSeconds)
        var secondsRemaining = config.durationSeconds

        tickRunnable = object : Runnable {
            override fun run() {
                secondsRemaining -= 1
                if (secondsRemaining <= 0) {
                    stopRecordingInternal(config, callback)
                    return
                }
                callback.onTick(secondsRemaining)
                mainHandler.postDelayed(this, 1_000L)
            }
        }
        mainHandler.postDelayed(tickRunnable!!, 1_000L)

        activeRecording = capture.output
            .prepareRecording(context, outputOptions)
            .withAudioEnabled()
            .start(ContextCompat.getMainExecutor(context)) { event ->
                when (event) {
                    is androidx.camera.video.VideoRecordEvent.Finalize -> {
                        if (event.hasError()) {
                            recordingInProgress.set(false)
                            callback.onFailure(
                                "Video recording failed: ${event.error}",
                                event.cause,
                            )
                        }
                    }
                    else -> Unit
                }
            }

        mainHandler.postDelayed(
            { stopRecordingInternal(config, callback) },
            config.durationSeconds * 1_000L,
        )
    }

    fun stopRecordingEarly(
        config: LiveCheckCaptureConfig = LiveCheckCaptureConfig(),
        callback: LiveCheckCaptureCallback,
    ) {
        stopRecordingInternal(config, callback)
    }

    fun release() {
        tickRunnable?.let { mainHandler.removeCallbacks(it) }
        tickRunnable = null
        activeRecording?.stop()
        activeRecording = null
        cameraProvider?.unbindAll()
        cameraProvider = null
        videoCapture = null
        cameraExecutor.shutdown()
    }

    private fun bindUseCases(provider: ProcessCameraProvider, previewView: PreviewView) {
        provider.unbindAll()

        val preview = Preview.Builder().build().also { useCase ->
            useCase.setSurfaceProvider(previewView.surfaceProvider)
        }

        val recorder = Recorder.Builder()
            .setQualitySelector(QualitySelector.from(Quality.HD))
            .build()
        val capture = VideoCapture.withOutput(recorder)
        videoCapture = capture

        provider.bindToLifecycle(
            lifecycleOwner,
            CameraSelector.DEFAULT_FRONT_CAMERA,
            preview,
            capture,
        )
    }

    private fun stopRecordingInternal(
        config: LiveCheckCaptureConfig,
        callback: LiveCheckCaptureCallback,
    ) {
        if (!stopRequested.compareAndSet(false, true)) {
            return
        }

        tickRunnable?.let { mainHandler.removeCallbacks(it) }
        tickRunnable = null

        val recording = activeRecording
        if (recording == null) {
            if (recordingInProgress.get()) {
                recordingInProgress.set(false)
                callback.onFailure("Recording was not started.")
            }
            return
        }

        recording.stop()
        activeRecording = null

        cameraExecutor.execute {
            try {
                val file = outputFile ?: error("Missing live-check output file.")
                waitForFile(file)

                val videoBytes = file.readBytes()
                val frames = LiveCheckFrameExtractor.extractJpegFrames(file, config.frameCount)
                if (frames.isEmpty()) {
                    error("Could not sample JPEG frames from the recorded clip.")
                }

                val result = LiveCheckCaptureResult(
                    videoBytes = videoBytes,
                    videoFilename = file.name,
                    videoContentType = config.videoContentType,
                    audioBytes = null,
                    audioFilename = null,
                    audioContentType = null,
                    frames = frames,
                )

                recordingInProgress.set(false)
                mainHandler.post { callback.onSuccess(result) }
            } catch (error: Throwable) {
                recordingInProgress.set(false)
                mainHandler.post {
                    callback.onFailure(error.message ?: "Live check processing failed.", error)
                }
            }
        }
    }

    private fun waitForFile(file: File, attempts: Int = 20, delayMs: Long = 100L) {
        repeat(attempts) {
            if (file.exists() && file.length() > 0L) {
                return
            }
            Thread.sleep(delayMs)
        }
        if (!file.exists() || file.length() == 0L) {
            error("Recorded video file is empty.")
        }
    }
}
