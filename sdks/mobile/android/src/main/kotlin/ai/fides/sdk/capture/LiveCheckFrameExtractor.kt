package ai.fides.sdk.capture

import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import java.io.ByteArrayOutputStream
import java.io.File

internal object LiveCheckFrameExtractor {
    fun extractJpegFrames(
        videoFile: File,
        frameCount: Int,
        jpegQuality: Int = 90,
    ): List<LiveCheckCaptureResult.CapturedFrame> {
        if (frameCount <= 0) {
            return emptyList()
        }

        val retriever = MediaMetadataRetriever()
        return try {
            retriever.setDataSource(videoFile.absolutePath)
            val durationMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
                ?.toLongOrNull()
                ?.coerceAtLeast(1L)
                ?: 10_000L

            buildList {
                for (index in 0 until frameCount) {
                    val timestampUs = durationMs * 1_000L * (index + 1) / (frameCount + 1)
                    val bitmap = retriever.getFrameAtTime(timestampUs, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
                        ?: continue
                    add(
                        LiveCheckCaptureResult.CapturedFrame(
                            index = index,
                            jpegBytes = bitmap.toJpegBytes(jpegQuality),
                        ),
                    )
                    bitmap.recycle()
                }
            }
        } finally {
            retriever.release()
        }
    }

    private fun Bitmap.toJpegBytes(quality: Int): ByteArray {
        val stream = ByteArrayOutputStream()
        compress(Bitmap.CompressFormat.JPEG, quality, stream)
        return stream.toByteArray()
    }
}
