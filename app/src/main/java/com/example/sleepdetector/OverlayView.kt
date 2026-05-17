package com.example.sleepdetector

import android.content.Context
import android.graphics.Canvas
import android.util.AttributeSet
import android.view.View

class OverlayView(context: Context, attrs: AttributeSet?) : View(context, attrs) {

    // Пустой класс — ничего не рисует
    fun updateOcclusionRegions(
        left: Boolean, right: Boolean, nose: Boolean, mouth: Boolean,
        lmks: Any
    ) {
        // Ничего не делаем, просто принимаем данные
    }

    fun clearOcclusionMap() {
        // Ничего не делаем
    }
}