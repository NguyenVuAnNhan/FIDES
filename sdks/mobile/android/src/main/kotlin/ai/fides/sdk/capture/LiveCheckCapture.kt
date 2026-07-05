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
import androidx.camera.video.Recording
import androidx.camera.video.VideoCapture
import androidx.camera.video.VideoRecordEvent
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
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
    private var videoCapture: VideoCapture<androidx.camera.video.Recorder>? = null
    private var boundPreviewView: PreviewView? = null
    private var activeRecording: Recording? = null
    private var outputFile: File? = null
    private var tickRunnable: Runnable? = null
    private val previewFrameRunnables = mutableListOf<Runnable>()
    private val previewFrames = mutableListOf<LiveCheckCaptureResult.CapturedFrame>()
    private var recordingFinalize: CountDownLatch? = null
    private var recordingFinalizeError: String? = null
    private val recordingInProgress = AtomicBoolean(false)
    private val stopRequested = AtomicBoolean(false)

    fun bindPreview(
        previewView: PreviewView,
        onReady: () -> Unit,
        onError: (String) -> Unit,
    ) {
        boundPreviewView = previewView
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
        recordingFinalizeError = null
        recordingFinalize = CountDownLatch(1)
        clearPreviewFrameCallbacks()
        previewFrames.clear()
        schedulePreviewFrameCaptures(config)

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
                if (event is VideoRecordEvent.Finalize) {
                    if (event.hasError()) {
                        recordingFinalizeError = "Video recording failed: ${event.error}"
                    }
                    recordingFinalize?.countDown()
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
        clearPreviewFrameCallbacks()
        tickRunnable?.let { mainHandler.removeCallbacks(it) }
        tickRunnable = null
        activeRecording?.stop()
        activeRecording = null
        cameraProvider?.unbindAll()
        cameraProvider = null
        videoCapture = null
        boundPreviewView = null
        cameraExecutor.shutdown()
    }

    private fun bindUseCases(provider: ProcessCameraProvider, previewView: PreviewView) {
        provider.unbindAll()

        val preview = Preview.Builder().build().also { useCase ->
            useCase.setSurfaceProvider(previewView.surfaceProvider)
        }

        val recorder = androidx.camera.video.Recorder.Builder()
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

    private fun schedulePreviewFrameCaptures(config: LiveCheckCaptureConfig) {
        for (index in 0 until config.frameCount) {
            val delayMs = config.durationSeconds * 1_000L * (index + 1) / (config.frameCount + 1)
            val runnable = Runnable { capturePreviewFrame(index) }
            previewFrameRunnables.add(runnable)
            mainHandler.postDelayed(runnable, delayMs)
        }
    }

    private fun capturePreviewFrame(index: Int) {
        if (!recordingInProgress.get()) {
            return
        }
        val view = boundPreviewView ?: return
        try {
            val bitmap = view.bitmap ?: return
            previewFrames.add(
                LiveCheckCaptureResult.CapturedFrame(
                    index = index,
                    jpegBytes = LiveCheckFrameExtractor.bitmapToJpegBytes(bitmap),
                ),
            )
            bitmap.recycle()
        } catch (_: Throwable) {
            // Preview sampling is best-effort; video extraction is the fallback.
        }
    }

    private fun clearPreviewFrameCallbacks() {
        previewFrameRunnables.forEach { mainHandler.removeCallbacks(it) }
        previewFrameRunnables.clear()
    }

    private fun stopRecordingInternal(
        config: LiveCheckCaptureConfig,
        callback: LiveCheckCaptureCallback,
    ) {
        if (!stopRequested.compareAndSet(false, true)) {
            return
        }

        clearPreviewFrameCallbacks()
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
                val finalizeLatch = recordingFinalize
                if (finalizeLatch != null && !finalizeLatch.await(15, TimeUnit.SECONDS)) {
                    error("Timed out waiting for the recorded clip to finalize.")
                }
                recordingFinalizeError?.let { error(it) }

                val file = outputFile ?: error("Missing live-check output file.")
                waitForFile(file)

                val videoBytes = file.readBytes()
                val frames = resolveFrames(
                    previewFrames = previewFrames.toList(),
                    videoFile = file,
                    frameCount = config.frameCount,
                )
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
                previewFrames.clear()
                mainHandler.post { callback.onSuccess(result) }
            } catch (error: Throwable) {
                recordingInProgress.set(false)
                previewFrames.clear()
                mainHandler.post {
                    callback.onFailure(error.message ?: "Live check processing failed.", error)
                }
            }
        }
    }

    private fun resolveFrames(
        previewFrames: List<LiveCheckCaptureResult.CapturedFrame>,
        videoFile: File,
        frameCount: Int,
    ): List<LiveCheckCaptureResult.CapturedFrame> {
        val sampled = previewFrames.sortedBy { it.index }
        if (sampled.size >= frameCount) {
            return sampled.take(frameCount)
        }

        val fromVideo = LiveCheckFrameExtractor.extractJpegFrames(videoFile, frameCount)
        if (sampled.isEmpty()) {
            return fromVideo
        }

        val usedIndexes = sampled.map { it.index }.toSet()
        return (sampled + fromVideo.filter { frame -> frame.index !in usedIndexes })
            .sortedBy { it.index }
            .take(frameCount)
    }

    private fun waitForFile(file: File, attempts: Int = 40, delayMs: Long = 150L) {
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
