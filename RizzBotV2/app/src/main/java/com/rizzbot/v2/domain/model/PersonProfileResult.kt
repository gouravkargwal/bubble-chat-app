package com.rizzbot.v2.domain.model

sealed class PersonProfileResult {
    data class Success(
        val name: String,
        val age: String?,
        val bio: String?,
        val interests: List<String>,
        val personalityTraits: List<String>,
        val fullExtraction: String
    ) : PersonProfileResult()

    data class Error(val message: String) : PersonProfileResult()
    data object Loading : PersonProfileResult()
}
