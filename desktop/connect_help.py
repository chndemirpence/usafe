"""Offline recovery copy and deliberately limited, local-only session evidence."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Advice:
    en: str
    tr: str
    action: str = ""


ADVICE = {
    "timeout": Advice("This bridge did not finish connecting. Check your internet connection and computer clock, then try another bridge method.",
                      "Bu köprü bağlantıyı tamamlayamadı. İnternet bağlantını ve bilgisayar saatini kontrol et, ardından başka bir köprü yöntemi dene.", "alternative"),
    "route_check": Advice("Tor started, but we could not verify internet access through it. Recheck the connection first. If it still fails, disconnect and try another method.",
                          "Tor başladı ancak üzerinden internet erişimini doğrulayamadık. Önce bağlantıyı tekrar doğrula. Sorun sürerse bağlantıyı kesip başka bir yöntem dene.", "alternative"),
    "tor_stopped": Advice("The Tor process stopped. Check that the complete USAFE package is extracted, then reconnect. A different bridge may help if the problem repeats.",
                          "Tor işlemi durdu. USAFE paketinin tamamını çıkardığını kontrol edip tekrar bağlan. Sorun sürerse başka bir köprü deneyebilirsin.", "alternative"),
    "runtime": Advice("The bundled connection files are missing or changed. Extract a fresh copy of the official USAFE Connect release into a new folder before connecting.",
                      "Bağlantı dosyaları eksik veya değişmiş. Bağlanmadan önce resmî USAFE Connect sürümünün yeni bir kopyasını ayrı bir klasöre çıkar."),
    "profile_busy": Advice("Another USAFE Connect session is using this profile. Disconnect that session before connecting here.",
                           "Başka bir USAFE Connect oturumu bu profili kullanıyor. Buradan bağlanmadan önce o oturumun bağlantısını kes."),
    "bridge_input": Advice("Paste 1–8 complete obfs4 or WebTunnel bridge lines from a trusted distributor. Keep each bridge on its own line, including its fingerprint and options.",
                           "Güvenilir bir kaynaktan 1–8 tam obfs4 veya WebTunnel köprü satırı yapıştır. Parmak izi ve seçenekler dahil her köprüyü ayrı bir satırda tut."),
    "cancelled": Advice("Connection stopped. You can choose a method and connect when you are ready.",
                        "Bağlantı durduruldu. Hazır olduğunda yöntem seçip bağlanabilirsin."),
    "unknown": Advice("The connection could not complete. Disconnect, check your internet connection and extracted app files, then try again. The offline guide has more help.",
                      "Bağlantı tamamlanamadı. Bağlantıyı kes, internetini ve çıkarılmış uygulama dosyalarını kontrol edip tekrar dene. Çevrimdışı rehberde daha fazla yardım var."),
}


def error_code(error):
    code = getattr(error, "code", "unknown")
    return code if code in ADVICE else "unknown"


def recovery_method(code, mode):
    if ADVICE.get(code, ADVICE["unknown"]).action != "alternative":
        return None
    return {"snowflake": "obfs4", "obfs4": "custom", "custom": "snowflake"}.get(mode)


OUTCOMES = ("not_answered", "completed", "needed_help", "could_not_complete")
DIFFICULTIES = ("not_answered", "none", "connection", "bridge_setup", "browser", "understanding_scope")


def attempt_record(mode, outcome, progress, elapsed, code=None):
    """Allowlisted structure: never copy arbitrary event fields or exception text."""
    if mode not in ("snowflake", "obfs4", "custom") or outcome not in ("verified", "failed", "cancelled"):
        raise ValueError("Invalid attempt category")
    return {"transport": mode, "outcome": outcome, "bootstrap_percent": max(0, min(100, int(progress))),
            "elapsed_seconds_rounded": max(0, round(elapsed / 5) * 5),
            "issue": code if code in ADVICE else None}


def connection_report(version, attempts, verified, state, outcome="not_answered", difficulty="not_answered"):
    if outcome not in OUTCOMES or difficulty not in DIFFICULTIES:
        raise ValueError("Choose a listed feedback option")
    clean = [attempt_record(item["transport"], item["outcome"], item["bootstrap_percent"],
                            item["elapsed_seconds_rounded"], item.get("issue")) for item in attempts[-10:]]
    return {"schema": 1, "app": "USAFE Connect", "version": version, "platform": "Windows",
            "scope": "Tor Browser launched by USAFE Connect", "current_route_verified": bool(verified),
            "state": state if state in ("ready", "connecting", "verifying", "connected", "error", "stopping", "offline") else "unknown",
            "attempts": clean, "feedback": {"task_outcome": outcome, "difficulty": difficulty}}


GUIDE = {
    "en": [
        ("Your first connection", "1. Choose Snowflake and select Connect. A bridge can take several minutes.\n\n2. Wait for Tor connection verified. The app checks an HTTPS request through Tor before enabling the browser button.\n\n3. Open Tor Browser here. Close any other Tor Browser window first. Browse inside the window opened by USAFE."),
        ("When a connection stalls", "Check that your internet connection works and your computer clock is correct. A stalled connection alone does not prove censorship.\n\nIf Snowflake times out, try obfs4. If included bridges do not work, select Custom and paste fresh obfs4 or WebTunnel bridges from a trusted distributor. You choose each new attempt; USAFE does not silently switch methods.\n\nObtain bridge instructions from the Tor Project: bridges.torproject.org or support.torproject.org. These addresses are provided as text; this guide makes no network requests. If the network has no working internet path, a bridge cannot create one."),
        ("What this connection covers", "This connection serves the Tor Browser launched here. Chrome, other apps and the Windows system connection are unchanged.\n\nA successful route check verifies Tor access at that moment. Use Recheck connection after changing Wi-Fi or when pages stop loading.\n\nDisconnect closes this managed Tor connection. Previously opened browser windows may remain visible with loaded pages, but cannot use the closed connection. Signing into an account can still identify you to that website."),
        ("Your data and feedback", "Connection attempts stay in memory for this app session (up to ten). The summary preview shows exactly what will be saved. Optional feedback uses fixed choices. Nothing is automatically sent.\n\nThe export excludes IP addresses, bridge lines, browsing URLs, raw logs and precise timestamps. The file still describes your use of USAFE; share it only if you choose.\n\nTor keeps local connection state on this device. Normal disconnect removes the private bridge configuration; abrupt power loss can leave temporary files. Closing the app does not erase downloaded files or browser data."),
    ],
    "tr": [
        ("İlk bağlantın", "1. Snowflake seçip Bağlan'a bas. Köprü bağlantısı birkaç dakika sürebilir.\n\n2. Tor bağlantısı doğrulandı yazısını bekle. Tarayıcı düğmesi açılmadan önce Tor üzerinden HTTPS erişimi kontrol edilir.\n\n3. Buradan Tor Browser'ı aç. Önce diğer Tor Browser pencerelerini kapat. USAFE'nin açtığı pencere içinde gezin."),
        ("Bağlantı ilerlemiyorsa", "İnternet bağlantının çalıştığını ve bilgisayar saatinin doğru olduğunu kontrol et. İlerlemeyen bağlantı tek başına sansür kanıtı değildir.\n\nSnowflake zaman aşımına uğrarsa obfs4 dene. Dahili köprüler çalışmıyorsa Özel köprü seçip güvenilir bir kaynaktan yeni obfs4 veya WebTunnel satırları yapıştır. Her yeni denemeyi sen başlatırsın; USAFE yöntemi sessizce değiştirmez.\n\nTor Project köprü rehberleri: bridges.torproject.org veya support.torproject.org. Bunlar metin olarak gösterilir; bu rehber ağ isteği yapmaz. Çalışan bir internet yolu yoksa köprü yeni bir internet bağlantısı oluşturamaz."),
        ("Bu bağlantının kapsamı", "Bağlantı, buradan açılan Tor Browser için geçerlidir. Chrome, diğer uygulamalar ve Windows sistem bağlantısı değişmez.\n\nBaşarılı doğrulama, o anda Tor erişimi olduğunu gösterir. Wi-Fi değiştirdikten veya sayfalar açılmamaya başladıktan sonra Bağlantıyı tekrar doğrula düğmesini kullan.\n\nBağlantıyı kesmek, bu Tor oturumunu kapatır. Açık tarayıcı pencereleri yüklenmiş sayfalarla görünmeye devam edebilir, ancak kapatılan bağlantıyı kullanamaz. Bir hesabına giriş yapmak seni o siteye tanıtabilir."),
        ("Verilerin ve geri bildirimin", "En fazla on bağlantı denemesi, uygulama oturumu boyunca bellekte tutulur. Özet önizlemesi kaydedilecek bilgileri aynen gösterir. İsteğe bağlı geri bildirim hazır seçeneklerden oluşur. Hiçbir şey otomatik gönderilmez.\n\nDışa aktarılan dosyada IP adresi, köprü satırı, gezinme adresi, ham günlük veya kesin saat bulunmaz. Dosya yine de USAFE kullanımını anlatır; paylaşma kararı sana aittir.\n\nTor bu cihazda yerel bağlantı durumunu saklar. Normal bağlantı kesme özel köprü yapılandırmasını kaldırır; ani elektrik kesintisinde geçici dosyalar kalabilir. Uygulamayı kapatmak indirilen dosyaları veya tarayıcı verilerini silmez."),
    ],
}
