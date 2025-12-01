# Mini App Buttons Guide - Complete Setup

## 🎯 What You Asked For

**"How can I make a button that opens a modal inside Telegram like my competitor?"**

**Answer:** You already have everything built! It's called **Telegram Web Apps (Mini Apps)**, and your miniapp at `/miniapp` is ready to use.

---

## ✨ How It Works

### Your Competitor's Flow:
1. User receives message with "Grab the Special Offer" button
2. Clicks button
3. Mini app opens **inside Telegram** (modal-like popup)
4. User can purchase/interact without leaving Telegram

### Your Flow (Now Available):
1. Create system message with Web App button
2. Set Web App URL to: `/miniapp?page=premium`
3. When users click, it opens YOUR Premium page inside Telegram
4. They can purchase using Telegram Stars!

**Exact same UX as your competitor!** 🎉

---

## 🚀 Quick Start - 3 Steps

### **Step 1: Go to System Messages**
Navigate to: System Messages → Create Message

### **Step 2: Add Message Text**
```
That girl in the GIF? She's waiting for your command...

Don't miss this rare chance to enjoy VIP access to the fullest!

This is a one-time purchase. No subscription. No auto-renewal.

👉 Activate VIP now – before this exclusive offer disappears!
```

### **Step 3: Add Web App Button**

In the "Buttons" section:
- **Button Text:** `🎁 Grab the Special Offer`
- **Web App URL:** `/miniapp?page=premium`

That's it! When users click, your Premium page opens inside Telegram.

---

## 📱 Available Mini App Pages

You have 2 pages already built:

| URL | Opens | Use Case |
|-----|-------|----------|
| `/miniapp?page=premium` | Premium/Settings page | Upsells, subscriptions, purchases |
| `/miniapp?page=gallery` | Character gallery | Announce new characters, re-engage |

---

## 🎨 UI Improvements Made

### 1. **Templates Page Enhanced**
- ✅ Quick setup guide with examples
- ✅ Copy-paste ready configurations
- ✅ Visual preview of how buttons work
- ✅ Liquid design with glassmorphism

### 2. **Delivery Stats - Full Error Display**
- ✅ Error column now 50% width (no truncation!)
- ✅ Hover to expand full error message
- ✅ Red background highlighting
- ✅ Monospace font for readability

### 3. **Modern Liquid Design**
- ✅ Glassmorphism effects
- ✅ Gradient backgrounds
- ✅ Smooth animations
- ✅ Professional polish

---

## 💰 Use Cases & Examples

### **Example 1: Premium Upsell**
```
Message:
⚡ Running Low on Energy?

Upgrade to Premium and unlock:
• ∞ Infinite energy
• 📸 Unlimited photos
• 👯 Advanced AI models

No subscription. Pay once, enjoy forever!

Button: "⚡ Get Premium"
Web App URL: /miniapp?page=premium
```

### **Example 2: Special Offer (Like Your Screenshot)**
```
Message:
That girl in the GIF? She's waiting for your command...

Don't miss this rare chance to enjoy VIP access to the fullest!

This is a one-time purchase. No subscription. No auto-renewal.

👉 Activate VIP now – before this exclusive offer disappears!

Button: "🎁 Grab the Special Offer"
Web App URL: /miniapp?page=premium
```

### **Example 3: New Characters**
```
Message:
🆕 New Characters Just Dropped!

We added 5 new AI companions with unique personalities and looks.

Check them out now!

Button: "✨ Explore New Characters"
Web App URL: /miniapp?page=gallery
```

---

## 🛠️ How to Create in Scheduler

### **Automated Premium Upsells**

You can trigger these automatically! For example, send to users who haven't purchased after 3 days:

1. **Create System Message** with Web App button
2. **Target:** Group = `inactive_7d` or specific users
3. **Schedule:** Set to send at specific time
4. **Status:** Will auto-send via scheduler

The scheduler (`app/core/scheduler.py`) already checks for scheduled messages every minute!

---

## 🔧 Technical Details

### How Web App Buttons Work

**Button Configuration (in your form):**
```javascript
{
  text: "🎁 Grab the Special Offer",
  web_app: {
    url: "/miniapp?page=premium"
  }
}
```

**What Telegram Does:**
1. Renders button with your text
2. On click, opens Web App in modal overlay
3. Loads your React miniapp with the specified page
4. User interacts without leaving Telegram
5. Can make purchases using Telegram Stars

**Backend (already implemented):**
```python
# app/core/system_message_service.py:238-243
if btn.get("web_app"):
    web_app = btn["web_app"]
    if isinstance(web_app, dict) and web_app.get("url"):
        web_app_info = WebAppInfo(url=web_app["url"])
        keyboard_buttons.append([InlineKeyboardButton(text=btn["text"], web_app=web_app_info)])
```

---

## 🎯 Complete Flow Example

### Scenario: Send Premium Offer to All Users

1. **Go to:** Dashboard → System Messages → Create Message

2. **Fill Form:**
   ```
   Title: Premium VIP Offer
   
   Message:
   That girl in the GIF? She's waiting for your command...
   
   Don't miss this rare chance to enjoy VIP access to the fullest!
   
   This is a one-time purchase. No subscription. No auto-renewal.
   
   👉 Activate VIP now – before this exclusive offer disappears!
   
   Media Type: Photo (optional)
   Media URL: https://your-image-url.com/offer.jpg
   
   Target: All Users
   Send: Immediately (or schedule)
   ```

3. **Add Button:**
   - Text: `🎁 Grab the Special Offer`
   - Web App URL: `/miniapp?page=premium`

4. **Click "Create"**

5. **Result:**
   - All users receive message
   - Click button → Mini app opens
   - Direct to premium purchase
   - Conversion! 💰

---

## 🔐 Security & URL Construction

### Full URL Construction

Your system automatically constructs the full URL:

```python
# From app/settings.py
@property
def public_url(self) -> str:
    if self.PUBLIC_BASE_URL:
        return self.PUBLIC_BASE_URL
    elif self.RAILWAY_PUBLIC_DOMAIN:
        return f"https://{self.RAILWAY_PUBLIC_DOMAIN}"
```

**In buttons, you use relative URLs:**
- `/miniapp?page=premium` → System converts to `https://your-domain.com/miniapp?page=premium`

**Telegram handles:**
- Authentication (via `initData`)
- Security
- Modal presentation
- Closing when done

---

## 📊 Tracking & Analytics

### Monitor Performance

After sending, check:
1. **Delivery Stats** - How many received
2. **Mini App Analytics** - How many opened
3. **Payment Analytics** - Conversion rate

### Available Metrics

Your system tracks:
- `system_message_deliveries` - Who received
- Mini app opens (via `WebApp.initData`)
- Purchases (in your payment handlers)

---

## ⚡ Pro Tips

### 1. **Test Before Broadcast**
- Target: "Single User" → Your own ID
- Send test message
- Click button to verify it opens correctly

### 2. **Use Compelling Copy**
- Urgency: "Limited time", "Don't miss"
- Benefit-focused: "Infinite energy", "Unlimited"
- Clear CTA: "Grab the Special Offer", "Get Premium"

### 3. **Schedule Wisely**
- Send during peak hours (check engagement heatmap!)
- Test different times
- A/B test messaging

### 4. **Combine with Scheduler**
- Auto-send to `inactive_7d` users
- Triggered after X days without purchase
- Re-engagement campaigns

---

## 🐛 Bug Fixes Applied

While setting this up, I also fixed:

1. ✅ **HTML Sanitization** - ReactQuill HTML now cleaned for Telegram
2. ✅ **Error Display** - Full error messages visible (no truncation)
3. ✅ **Media Messages** - Removed invalid `disable_web_page_preview` parameter
4. ✅ **Structured Logging** - Better error tracking

---

## 📁 Files Modified

1. ✅ `analytics-dashboard/src/components/SystemMessageTemplates.jsx` - Quick setup guide
2. ✅ `analytics-dashboard/src/components/SystemMessageDeliveryStats.jsx` - Full error display
3. ✅ `app/core/system_message_service.py` - HTML sanitization + bug fixes

---

## ✅ Summary

**You asked:** "How can I make buttons open my Settings page?"

**Answer:** It's already built! Just use:
- **Button Text:** Whatever you want (e.g., "🎁 Grab the Special Offer")
- **Web App URL:** `/miniapp?page=premium`

**When user clicks:**
- 📱 Mini app opens inside Telegram
- 🎯 Direct to Premium purchase page
- ⚡ Instant conversion flow

**Same as your competitor's implementation!** 🎉

---

## 🚀 Next Steps

1. Go to **Templates** tab in dashboard
2. See the examples with Mini App buttons
3. Copy an example or create your own
4. Send a test message to yourself
5. Click the button → See your Premium page open!

That's it! You're ready to drive conversions with in-Telegram purchases! 💰

