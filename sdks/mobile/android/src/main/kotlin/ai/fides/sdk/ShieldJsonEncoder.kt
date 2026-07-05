package ai.fides.sdk

import org.json.JSONArray
import org.json.JSONObject

object ShieldJsonEncoder {
    fun encode(map: Map<String, Any?>): String = toJsonObject(map).toString()

    fun toJsonObject(map: Map<String, Any?>): JSONObject {
        val json = JSONObject()
        map.forEach { (key, value) -> json.putValue(key, value) }
        return json
    }

    private fun JSONObject.putValue(key: String, value: Any?) {
        when (value) {
            null -> put(key, JSONObject.NULL)
            is Map<*, *> -> put(key, toJsonObject(value as Map<String, Any?>))
            is List<*> -> put(key, toJsonArray(value))
            else -> put(key, value)
        }
    }

    private fun toJsonArray(values: List<*>): JSONArray {
        val array = JSONArray()
        values.forEach { value ->
            when (value) {
                null -> array.put(JSONObject.NULL)
                is Map<*, *> -> array.put(toJsonObject(value as Map<String, Any?>))
                is List<*> -> array.put(toJsonArray(value))
                else -> array.put(value)
            }
        }
        return array
    }
}
