package ai.fides.sdk.capture

data class LiveCheckCaptureConfig(
    val durationSeconds: Int = 10,
    val frameCount: Int = 3,
    val videoContentType: String = "video/mp4",
    val audioContentType: String = "audio/mp4",
)

data class LiveCheckCaptureResult(
    val videoBytes: ByteArray,
    val videoFilename: String,
    val videoContentType: String,
    val audioBytes: ByteArray?,
    val audioFilename: String?,
    val audioContentType: String?,
    val frames: List<CapturedFrame>,
) {
    data class CapturedFrame(
        val index: Int,
        val jpegBytes: ByteArray,
        val filename: String = "frame-$index.jpg",
    )
}

interface LiveCheckCaptureCallback {
    fun onPreviewReady() {}
    fun onRecordingStarted(durationSeconds: Int) {}
    fun onTick(secondsRemaining: Int) {}
    fun onSuccess(result: LiveCheckCaptureResult)
    fun onFailure(message: String, cause: Throwable? = null)
}
