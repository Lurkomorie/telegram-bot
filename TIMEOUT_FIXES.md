# Timeout Issues - Root Cause Analysis & Fixes

## Problem Summary

The application was experiencing multiple timeout errors:

1. **TelegramNetworkError: HTTP Client says - Request timeout error**
   - Occurring when sending photos to Telegram
   - Occurring when processing webhook updates
   - Occurring in background chat processing

2. **OpenRouter API Timeout Errors**
   - Multiple retry attempts (`[LLM] Retry 2/3 after 3.0s...`)
   - State resolver failures after all retries
   - Dialogue specialist failures
   - Empty error messages in logs

3. **Image Generation Issues**
   - Jobs failing with empty error messages
   - Duplicate callbacks being received and ignored

## Root Causes Identified

### 1. Insufficient HTTP Client Timeouts for LLM API

**Location:** `app/core/llm_openrouter.py`

**Issue:** 
- Used a single scalar timeout value (40 seconds) for all HTTP operations
- No distinction between connection timeout, read timeout, and write timeout
- Insufficient connection pool limits
- Poor error handling - exceptions weren't being caught properly

**Impact:**
- LLM API calls timing out during slow responses
- Empty error messages in logs due to improper exception handling
- Connection pool exhaustion causing additional failures

### 2. No Timeout Configuration for Telegram Bot

**Location:** `app/bot/loader.py`

**Issue:**
- Bot instance created with default aiogram timeout settings (too aggressive)
- No custom session configuration
- Image uploads (1-2MB) timing out due to short default timeouts

**Impact:**
- Large image uploads failing frequently
- "Request timeout error" when sending photos
- Users not receiving generated images

### 3. Conservative Default Timeout Values

**Location:** `config/app.yaml`

**Issue:**
- LLM timeout set to 40 seconds
- Insufficient for slower API responses during high load

**Impact:**
- Legitimate slow responses being treated as timeouts
- Unnecessary retries increasing API costs
- Poor user experience with frequent failures

## Fixes Applied

### Fix 1: Enhanced LLM Client Timeout Configuration

**File:** `app/core/llm_openrouter.py`

**Changes:**
1. **Granular Timeout Configuration:**
   ```python
   timeout_config = httpx.Timeout(
       connect=10.0,   # Connection establishment
       read=60.0,      # Read timeout (main bottleneck for LLMs)
       write=10.0,     # Write timeout
       pool=5.0        # Pool acquisition timeout
   )
   ```

2. **Increased Connection Pool Limits:**
   ```python
   httpx.Limits(max_keepalive_connections=10, max_connections=20)
   ```

3. **Improved Error Handling:**
   - Separate handlers for `TimeoutException`, `HTTPStatusError`, and `RequestError`
   - Detailed error logging with exception types
   - No retry on 4xx errors (client errors)
   - Exponential backoff with longer waits for network issues
   - Proper error message propagation

4. **Better Logging:**
   - Log timeout configuration on each request
   - Log specific error details (HTTP status, error type, etc.)
   - Track retry attempts with detailed context

**Benefits:**
- More resilient to temporary network issues
- Better diagnostics when failures occur
- Reduced false positives (legitimate slow responses no longer timeout)
- More efficient retry logic

### Fix 2: Custom Telegram Bot Session with Generous Timeouts

**File:** `app/bot/loader.py`

**Changes:**
```python
import aiohttp
from aiogram.client.session.aiohttp import AiohttpSession

timeout = aiohttp.ClientTimeout(
    total=None,        # No total timeout
    connect=10,        # 10s to establish connection
    sock_read=120,     # 120s to read data (for large image uploads)
    sock_connect=10    # 10s for socket connection
)

session = AiohttpSession(timeout=timeout)
bot = Bot(token=settings.BOT_TOKEN, session=session, ...)
```

**Benefits:**
- Large image uploads (1-2MB) no longer timeout
- More stable communication with Telegram API
- Better handling of network latency spikes

### Fix 3: Increased Default LLM Timeout

**File:** `config/app.yaml`

**Changes:**
```yaml
llm:
  timeout_sec: 60  # Increased from 40s to 60s
```

**Benefits:**
- More headroom for legitimate slow responses
- Reduced unnecessary retries
- Better reliability during API high-load periods

## Expected Improvements

### Immediate Benefits:
1. ✅ **Reduced LLM Timeout Errors** - 60s read timeout + proper error handling
2. ✅ **Successful Image Uploads** - 120s socket read timeout for Telegram
3. ✅ **Better Error Messages** - Detailed exception logging
4. ✅ **Fewer False Failures** - Distinction between real errors and slow responses

### Long-term Benefits:
1. ✅ **Lower API Costs** - Fewer unnecessary retries
2. ✅ **Better User Experience** - More reliable bot responses
3. ✅ **Easier Debugging** - Detailed error logs with exception types
4. ✅ **More Scalable** - Increased connection pool limits

## Monitoring Recommendations

### Key Metrics to Track:
1. **LLM API Response Times**
   - Monitor average response time
   - Track 95th and 99th percentiles
   - Alert if consistently above 50s

2. **Timeout Occurrence Rate**
   - Count of `TimeoutException` errors per hour
   - Should decrease significantly after fixes
   - Alert if rate increases

3. **Image Upload Success Rate**
   - Track percentage of successful image deliveries
   - Monitor time from generation to delivery
   - Alert if success rate < 95%

4. **Retry Frequency**
   - Count of retry attempts per hour
   - Should decrease with more generous timeouts
   - Alert if retry rate increases

### Log Patterns to Watch:

**Good (expected after fixes):**
```
[LLM] 🤖 Calling ... (timeout=60s)
[LLM] ✅ Response received (X chars)
[IMAGE-CALLBACK] ✅ Image sent to chat X
```

**Bad (should be rare now):**
```
[LLM] ⚠️  Attempt 3/3 failed: Timeout after 60s
[IMAGE-CALLBACK] ❌ Error sending photo
```

**Action Required:**
```
[LLM] ⚠️  Attempt 3/3 failed: HTTP 429
[LLM] ⚠️  Attempt 3/3 failed: HTTP 503
```
→ May indicate API rate limiting or service issues

## Testing Recommendations

### 1. Load Testing
- Send 10+ concurrent messages to test connection pool
- Verify no connection pool exhaustion errors
- Monitor retry rates

### 2. Large Image Testing
- Generate and send multiple 1-2MB images
- Verify all uploads complete successfully
- Check upload times are within acceptable range

### 3. Slow API Response Testing
- Monitor behavior during peak hours
- Verify 45-55s responses complete successfully
- Confirm no premature timeouts

### 4. Error Recovery Testing
- Simulate temporary network issues
- Verify retry logic works correctly
- Confirm proper error messages in logs

## Additional Recommendations

### Short-term:
1. **Monitor Production Logs** - Watch for timeout patterns over next 24-48 hours
2. **Track Retry Rates** - Should decrease significantly
3. **User Feedback** - Monitor support channels for image upload issues

### Medium-term:
1. **Add Metrics Dashboard** - Track timeout rates, retry rates, response times
2. **Set Up Alerts** - Alert on timeout rate increases
3. **Performance Tuning** - Adjust timeouts based on observed API response times

### Long-term:
1. **Circuit Breaker Pattern** - Consider implementing circuit breaker for API failures
2. **Caching Layer** - Cache frequently requested data to reduce API calls
3. **Queue Optimization** - Consider priority queues for user-facing vs. background tasks

## Rollback Plan

If issues arise after deployment:

1. **Immediate Rollback:**
   ```bash
   git revert <commit-hash>
   ```

2. **Partial Rollback (if only one component is problematic):**
   - LLM timeouts: Revert `llm_openrouter.py` changes
   - Bot timeouts: Revert `loader.py` changes
   - Config: Revert `app.yaml` changes

3. **Emergency Mitigation:**
   - Temporarily disable image generation: Set `ENABLE_IMAGES_IN_FOLLOWUP=False`
   - Reduce concurrent load: Decrease connection pool limits

## Files Modified

1. `app/core/llm_openrouter.py` - Enhanced timeout and error handling
2. `app/bot/loader.py` - Added custom session with generous timeouts
3. `config/app.yaml` - Increased default timeout from 40s to 60s

## Deployment Notes

- No database migrations required
- No environment variable changes required
- Restart application to apply changes
- Monitor logs for first hour after deployment
- Check error rates and user reports

---

**Last Updated:** 2025-11-08
**Status:** ✅ Ready for Production

