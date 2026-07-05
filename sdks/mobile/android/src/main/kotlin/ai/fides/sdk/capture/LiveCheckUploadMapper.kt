package ai.fides.sdk.capture

import ai.fides.sdk.LiveCheckFramePart
import ai.fides.sdk.LiveCheckUploadInput

fun LiveCheckCaptureResult.toUploadInput(
    documentBytes: ByteArray,
    documentFilename: String,
    documentContentType: String = "image/jpeg",
): LiveCheckUploadInput =
    LiveCheckUploadInput(
        challengeVideo = videoBytes,
        challengeVideoFilename = videoFilename,
        challengeVideoContentType = videoContentType,
        document = documentBytes,
        documentFilename = documentFilename,
        documentContentType = documentContentType,
        challengeAudio = audioBytes,
        challengeAudioFilename = audioFilename,
        challengeAudioContentType = audioContentType ?: "audio/webm",
        frames = frames.map { frame ->
            LiveCheckFramePart(
                index = frame.index,
                jpegBytes = frame.jpegBytes,
                filename = frame.filename,
            )
        },
    )
