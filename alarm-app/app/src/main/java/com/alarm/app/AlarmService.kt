package com.alarm.app

import android.app.Service
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.ln
import kotlin.random.Random

class AlarmService : Service() {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val alerts = listOf(
        "Воздушная тревога",
        "Беспилотная опасность",
        "Ракетная опасность"
    )

    override fun onCreate() {
        super.onCreate()
        startForeground(NOTIFICATION_ID, createServiceNotification())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        scope.launch {
            while (isActive) {
                val interval = randomInterval()
                delay(interval)
                val alert = alerts.random()
                showAlertNotification(alert)
            }
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    private fun randomInterval(): Long {
        val mean = 900_000L
        val min = 300_000L
        val max = 7_200_000L
        val raw = (-ln(Random.nextDouble())) * mean * 1.5 + Random.nextLong(-600_000, 600_000)
        return raw.toLong().coerceIn(min, max)
    }

    private fun createServiceNotification() =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Рандомайзер тревог")
            .setContentText("Активен")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setOngoing(true)
            .build()

    private fun showAlertNotification(alert: String) {
        val dateFormat = SimpleDateFormat("dd.MM.yyyy HH:mm:ss", Locale.getDefault())
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(alert)
            .setContentText("Время: ${dateFormat.format(Date())}")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setAutoCancel(true)
            .build()

        val manager = getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager
        manager.notify(System.currentTimeMillis().toInt(), notification)
    }

    companion object {
        const val CHANNEL_ID = "alarm_channel"
        const val NOTIFICATION_ID = 1
    }
}
