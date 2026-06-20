package com.alarm.app

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {
    private lateinit var btnStart: Button
    private lateinit var btnStop: Button
    private lateinit var tvCountdown: TextView
    private lateinit var tvStatus: TextView
    private lateinit var etMin: EditText
    private lateinit var etMax: EditText

    private val handler = Handler(Looper.getMainLooper())
    private val countdownRunnable = object : Runnable {
        override fun run() {
            updateCountdown()
            handler.postDelayed(this, 1000)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        NotificationHelper.createChannel(this)
        requestNotificationPermission()

        tvCountdown = findViewById(R.id.tvCountdown)
        tvStatus = findViewById(R.id.tvStatus)
        btnStart = findViewById(R.id.btnStart)
        btnStop = findViewById(R.id.btnStop)
        etMin = findViewById(R.id.etMinInterval)
        etMax = findViewById(R.id.etMaxInterval)

        loadSettings()

        btnStart.setOnClickListener {
            saveSettings()
            startForegroundService(Intent(this, AlarmService::class.java))
            btnStart.isEnabled = false
            btnStop.isEnabled = true
        }

        btnStop.setOnClickListener {
            stopService(Intent(this, AlarmService::class.java))
            btnStart.isEnabled = true
            btnStop.isEnabled = false
            tvCountdown.text = "—"
            tvStatus.text = "Остановлен"
        }
    }

    override fun onResume() {
        super.onResume()
        updateButtons()
        handler.post(countdownRunnable)
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(countdownRunnable)
    }

    private fun updateButtons() {
        val running = AlarmService.isRunning
        btnStart.isEnabled = !running
        btnStop.isEnabled = running
    }

    private fun updateCountdown() {
        val nextTime = AlarmService.nextAlertTime
        if (nextTime > 0) {
            val remaining = nextTime - System.currentTimeMillis()
            if (remaining > 0) {
                tvCountdown.text = formatTime(remaining)
                tvStatus.text = "Активен"
            } else if (AlarmService.isRunning) {
                tvCountdown.text = "Скоро..."
                tvStatus.text = "Активен"
            }
        } else if (!AlarmService.isRunning) {
            tvCountdown.text = "—"
            tvStatus.text = "Остановлен"
        }
    }

    private fun formatTime(millis: Long): String {
        val totalSec = millis / 1000
        val hours = totalSec / 3600
        val minutes = (totalSec % 3600) / 60
        val seconds = totalSec % 60
        return if (hours > 0) {
            String.format("%d:%02d:%02d", hours, minutes, seconds)
        } else {
            String.format("%02d:%02d", minutes, seconds)
        }
    }

    private fun loadSettings() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val minMin = prefs.getLong("min_interval", 5)
        val maxMin = prefs.getLong("max_interval", 120)
        etMin.setText(minMin.toString())
        etMax.setText(maxMin.toString())
    }

    private fun saveSettings() {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        var min = etMin.text.toString().toLongOrNull()?.coerceIn(1, 999) ?: 5
        var max = etMax.text.toString().toLongOrNull()?.coerceIn(1, 999) ?: 120
        if (min > max) {
            val tmp = min; min = max; max = tmp
            Toast.makeText(this, "Мин и макс интервал поменяны местами", Toast.LENGTH_SHORT).show()
        }
        etMin.setText(min.toString())
        etMax.setText(max.toString())
        prefs.edit()
            .putLong("min_interval", min)
            .putLong("max_interval", max)
            .apply()
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    100
                )
            }
        }
    }

    companion object {
        const val PREFS_NAME = "alarm_prefs"
    }
}
