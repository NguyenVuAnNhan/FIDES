package ai.fides.sdk.capture

import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.os.Build
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

            val frames = buildList {
                for (index in 0 until frameCount) {
                    val timestampUs = durationMs * 1_000L * (index + 1) / (frameCount + 1)
                    val bitmap = retriever.getFrameAtTime(timestampUs, MediaMetadataRetriever.OPTION_CLOSEST)
                        ?: retriever.getFrameAtTime(timestampUs, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
                        ?: retriever.getFrameAtTime(0, MediaMetadataRetriever.OPTION_CLOSEST)
                    if (bitmap != null) {
                        add(
                            LiveCheckCaptureResult.CapturedFrame(
                                index = index,
                                jpegBytes = bitmap.toJpegBytes(jpegQuality),
                            ),
                        )
                        bitmap.recycle()
                    }
                }
            }

            if (frames.isNotEmpty()) {
                frames
            } else {
                extractByFrameIndex(retriever, frameCount, jpegQuality)
            }
        } finally {
            retriever.release()
        }
    }

    fun bitmapToJpegBytes(bitmap: Bitmap, jpegQuality: Int = 90): ByteArray =
        bitmap.toJpegBytes(jpegQuality)

    private fun extractByFrameIndex(
        retriever: MediaMetadataRetriever,
        frameCount: Int,
        jpegQuality: Int,
    ): List<LiveCheckCaptureResult.CapturedFrame> {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) {
            return emptyList()
        }

        val totalFrames = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_FRAME_COUNT)
            ?.toLongOrNull()
            ?.coerceAtLeast(1L)
            ?: return emptyList()

        return buildList {
            for (index in 0 until frameCount) {
                val frameIndex = totalFrames * (index + 1) / (frameCount + 1)
                val bitmap = retriever.getFrameAtIndex(frameIndex.toInt())
                if (bitmap != null) {
                    add(
                        LiveCheckCaptureResult.CapturedFrame(
                            index = index,
                            jpegBytes = bitmap.toJpegBytes(jpegQuality),
                        ),
                    )
                    bitmap.recycle()
                }
            }
        }
    }

    private fun Bitmap.toJpegBytes(quality: Int): ByteArray {
        val stream = ByteArrayOutputStream()
        compress(Bitmap.CompressFormat.JPEG, quality, stream)
        return stream.toByteArray()
    }
}
