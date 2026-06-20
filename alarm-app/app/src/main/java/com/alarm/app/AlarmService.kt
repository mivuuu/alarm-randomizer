package com.alarm.app

import android.app.Service
import android.content.Context
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

    private data class Region(val name: String, val weight: Int)

    private val alerts = listOf(
        "Воздушная тревога",
        "Беспилотная опасность",
        "Ракетная опасность"
    )

    private val regions = listOf(
        Region("Калантия", 5),
        Region("Альтерия", 5),
        Region("Сильвания", 5),
        Region("Таврия", 5),
        Region("Валентия", 5),
        Region("Иллирия", 5),
        Region("Астралия", 5),
        Region("Лимнида", 5),
        Region("Монтания", 5),
        Region("Меридиония", 5),
        Region("Эстерия", 5),
        Region("Гесперия", 3),
        Region("Ориентия", 3),
        Region("Люциния", 3),
        Region("Нереида", 3),
        Region("Аргезия", 3),
        Region("Наяда", 3),
        Region("Люмена", 3),
        Region("Солария", 3),
        Region("Небулия", 3),
        Region("Медиолания", 3),
        Region("Джаннат-аль-амн", 3),
        Region("Мариния", 3),
        Region("Иудейская автономия", 1),
        Region("Салабимия", 1),
        Region("Эндор", 1),
        Region("Сидерия", 1),
        Region("Селения", 1),
        Region("Кастелия", 1),
        Region("Окцидентия", 1),
        Region("Виридия", 1),
        Region("Тенебрия", 1),
        Region("Ойл", 1),
        Region("Гесперидия", 1),
    )

    override fun onCreate() {
        super.onCreate()
        isRunning = true
        startForeground(NOTIFICATION_ID, createServiceNotification())
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        scope.launch {
            while (isActive) {
                val interval = randomInterval()
                nextAlertTime = System.currentTimeMillis() + interval
                delay(interval)

                val alert = alerts.random()
                val strength = randomStrength()
                val count = regionCount(strength)
                val selected = selectRegions(count)
                showAlertNotification(alert, strength, selected)

                nextAlertTime = 0
            }
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        isRunning = false
        nextAlertTime = 0
        scope.cancel()
        super.onDestroy()
    }

    private fun randomInterval(): Long {
        val prefs = getSharedPreferences(MainActivity.PREFS_NAME, Context.MODE_PRIVATE)
        val minMin = prefs.getLong("min_interval", 5)
        val maxMin = prefs.getLong("max_interval", 120)
        val min = minMin * 60_000L
        val max = maxMin * 60_000L
        val mean = (min + max) / 2
        val jitter = (max - min) / 8
        val raw = (-ln(Random.nextDouble())) * mean * 1.5 + Random.nextLong(-jitter, jitter)
        return raw.toLong().coerceIn(min, max)
    }

    private fun randomStrength(): Int {
        val raw = (-ln(Random.nextDouble())) * 2.5 + 1
        return raw.toInt().coerceIn(1, 10)
    }

    private fun regionCount(strength: Int): Int = when (strength) {
        1 -> 1
        2 -> 1
        3 -> 2
        4 -> 2
        5 -> 3
        6 -> 4
        7 -> Random.nextInt(4, 6)
        8 -> Random.nextInt(5, 8)
        9 -> Random.nextInt(7, 10)
        10 -> Random.nextInt(9, 13)
        else -> 1
    }

    private fun selectRegions(count: Int): List<String> {
        val pool = regions.toMutableList()
        val result = mutableListOf<String>()
        val n = count.coerceAtMost(pool.size)
        repeat(n) {
            val totalWeight = pool.sumOf { it.weight }
            var r = Random.nextDouble() * totalWeight
            var idx = 0
            for (i in pool.indices) {
                r -= pool[i].weight
                if (r <= 0) {
                    idx = i
                    break
                }
            }
            result.add(pool[idx].name)
            pool.removeAt(idx)
        }
        return result
    }

    private fun createServiceNotification() =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Рандомайзер тревог")
            .setContentText("Активен")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setOngoing(true)
            .build()

    private fun showAlertNotification(alert: String, strength: Int, selected: List<String>) {
        val dateFormat = SimpleDateFormat("dd.MM.yyyy HH:mm:ss", Locale.getDefault())
        val regionsText = selected.joinToString(", ")
        val body = "Сила: $strength | Регионы (${selected.size}): $regionsText\nВремя: ${dateFormat.format(Date())}"
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(alert)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setAutoCancel(true)
            .build()

        val manager = getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager
        manager.notify(System.currentTimeMillis().toInt(), notification)
    }

    companion object {
        var nextAlertTime: Long = 0
        var isRunning: Boolean = false
        const val CHANNEL_ID = "alarm_channel"
        const val NOTIFICATION_ID = 1
    }
}
