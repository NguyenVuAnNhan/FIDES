package ai.fides.sdk

import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException

/**
 * Reference HTTP transport for host apps using OkHttp.
 * Add `implementation("com.squareup.okhttp3:okhttp:4.12.0")` in the banking app module.
 */
class OkHttpFidesTransport(
    private val client: OkHttpClient = OkHttpClient(),
    private val authHeaderProvider: (() -> String?)? = null,
) : FidesHttpTransport {
    override fun postJson(
        baseUrl: String,
        path: String,
        body: Map<String, Any?>,
        completion: (FidesSdkResult<String>) -> Unit,
    ) {
        val jsonBody = ShieldJsonEncoder.encode(body)
            .toRequestBody("application/json; charset=utf-8".toMediaType())

        val requestBuilder = Request.Builder()
            .url(normalizeBaseUrl(baseUrl) + path)
            .post(jsonBody)

        authHeaderProvider?.invoke()?.let { token ->
            requestBuilder.header("Authorization", token)
        }

        client.newCall(requestBuilder.build()).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                completion(FidesSdkResult.Failure(e.message ?: "Network request failed.", e))
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    val bodyText = it.body?.string().orEmpty()
                    if (!it.isSuccessful) {
                        completion(FidesSdkResult.Failure(bodyText.ifBlank { "HTTP ${it.code}" }))
                        return
                    }
                    completion(FidesSdkResult.Success(bodyText))
                }
            }
        })
    }

    override fun postMultipart(
        baseUrl: String,
        path: String,
        parts: List<MultipartPart>,
        completion: (FidesSdkResult<String>) -> Unit,
    ) {
        val multipartBuilder = okhttp3.MultipartBody.Builder().setType(okhttp3.MultipartBody.FORM)
        parts.forEach { part ->
            multipartBuilder.addFormDataPart(
                part.fieldName,
                part.filename,
                part.bytes.toRequestBody(part.contentType.toMediaType()),
            )
        }

        val requestBuilder = Request.Builder()
            .url(normalizeBaseUrl(baseUrl) + path)
            .post(multipartBuilder.build())

        authHeaderProvider?.invoke()?.let { token ->
            requestBuilder.header("Authorization", token)
        }

        client.newCall(requestBuilder.build()).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                completion(FidesSdkResult.Failure(e.message ?: "Network request failed.", e))
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    val bodyText = it.body?.string().orEmpty()
                    if (!it.isSuccessful) {
                        completion(FidesSdkResult.Failure(bodyText.ifBlank { "HTTP ${it.code}" }))
                        return
                    }
                    completion(FidesSdkResult.Success(bodyText))
                }
            }
        })
    }

    private fun normalizeBaseUrl(baseUrl: String): String =
        baseUrl.trimEnd('/')
}
