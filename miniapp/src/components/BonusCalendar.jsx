import WebApp from "@twa-dev/sdk";
import { useEffect, useState } from "react";
import lightningIcon from "../assets/lightning.webp";
import { useTranslation } from "../i18n/TranslationContext";
import "./BonusCalendar.css";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? "http://localhost:8000" : "");

// 30-day bonus calendar with progressive rewards
// Total: 550 tokens + 50 completion bonus = 600 tokens max per cycle
const BONUS_CALENDAR = [
  5,
  5,
  10,
  10,
  10,
  10,
  15, // Week 1 (65)
  15,
  15,
  15,
  15,
  15,
  20,
  20, // Week 2 (115)
  20,
  20,
  20,
  20,
  20,
  25,
  25, // Week 3 (150)
  25,
  25,
  25,
  30,
  30,
  35,
  50, // Week 4 (220)
];
const DAY_30_COMPLETION_BONUS = 50;

export default function BonusCalendar({ onClose, onClaim }) {
  const { t } = useTranslation();
  const [calendarData, setCalendarData] = useState({
    calendar: BONUS_CALENDAR,
    current_day: 1,
    can_claim: false,
    next_bonus_in_seconds: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isClaiming, setIsClaiming] = useState(false);

  useEffect(() => {
    loadCalendarData();
  }, []);

  async function loadCalendarData() {
    try {
      setIsLoading(true);
      const initData = WebApp.initData;
      const response = await fetch(`${API_BASE}/api/miniapp/bonus-calendar`, {
        headers: {
          "X-Telegram-Init-Data": initData || "",
        },
      });

      if (response.ok) {
        const data = await response.json();
        setCalendarData(data);
      }
    } catch (error) {
      console.error("Failed to load calendar data:", error);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleClaim() {
    if (isClaiming || !calendarData.can_claim) return;

    setIsClaiming(true);

    try {
      const initData = WebApp.initData;
      const response = await fetch(
        `${API_BASE}/api/miniapp/claim-daily-bonus`,
        {
          method: "POST",
          headers: {
            "X-Telegram-Init-Data": initData || "",
          },
        },
      );

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          // Update local state
          const isCalendarComplete = result.is_calendar_complete;
          setCalendarData((prev) => ({
            ...prev,
            can_claim: false,
            current_day: isCalendarComplete ? 1 : prev.current_day + 1,
            next_bonus_in_seconds: 86400,
          }));

          // Notify parent
          if (onClaim) {
            onClaim(result);
          }

          // Show appropriate message
          if (isCalendarComplete) {
            WebApp.showAlert(
              t("bonusCalendar.calendarComplete", {
                amount: result.bonus_amount,
                bonus: result.completion_bonus || DAY_30_COMPLETION_BONUS,
              }),
            );
          } else {
            WebApp.showAlert(
              t("bonusCalendar.claimSuccess", { amount: result.bonus_amount }),
            );
          }
        }
      }
    } catch (error) {
      console.error("Failed to claim bonus:", error);
      WebApp.showAlert(t("bonusCalendar.claimFailed"));
    } finally {
      setIsClaiming(false);
    }
  }

  function formatTimeRemaining(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}${t("app.time.hours")} ${minutes}${t("app.time.minutes")}`;
  }

  function getDayStatus(dayIndex) {
    const day = dayIndex + 1;
    if (day < calendarData.current_day) return "claimed";
    if (day === calendarData.current_day)
      return calendarData.can_claim ? "current" : "today";
    return "future";
  }

  return (
    <div className="bonus-calendar-overlay" onClick={onClose}>
      <div
        className="bonus-calendar-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="calendar-close-btn" onClick={onClose}>
          ×
        </button>

        <div className="calendar-header">
          <div className="calendar-header-icon">🎁</div>
          <h2 className="calendar-title">{t("bonusCalendar.title")}</h2>
          <p className="calendar-subtitle">{t("bonusCalendar.subtitle")}</p>
        </div>

        {isLoading ? (
          <div className="calendar-loading">
            <div className="calendar-spinner"></div>
          </div>
        ) : (
          <>
            <div className="calendar-grid calendar-grid-30">
              {BONUS_CALENDAR.map((amount, index) => {
                const status = getDayStatus(index);
                const isLastDay = index === 29; // Day 30

                return (
                  <div
                    key={index}
                    className={`calendar-day ${status} ${isLastDay ? "big-prize" : ""}`}
                  >
                    <span className="day-number">
                      {t("bonusCalendar.day", { day: index + 1 })}
                    </span>
                    <div className="day-amount">
                      <img
                        src={lightningIcon}
                        alt="tokens"
                        className="day-icon"
                      />
                      <span className="day-value">{amount}</span>
                    </div>
                    {status === "claimed" && (
                      <div className="day-checkmark">✓</div>
                    )}
                    {status === "current" && <div className="day-pulse"></div>}
                  </div>
                );
              })}
            </div>

            <div className="calendar-action">
              {calendarData.can_claim ? (
                <button
                  className="claim-btn"
                  onClick={handleClaim}
                  disabled={isClaiming}
                >
                  {isClaiming
                    ? t("bonusCalendar.claiming")
                    : t("bonusCalendar.claimButton")}
                </button>
              ) : (
                <div className="next-claim-info">
                  <span className="next-claim-label">
                    {t("bonusCalendar.nextBonus")}
                  </span>
                  <span className="next-claim-time">
                    {formatTimeRemaining(calendarData.next_bonus_in_seconds)}
                  </span>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
