#!/usr/bin/env bash
# CF designer-approval tracker (autonomous, zero user input).
# Email with the request was sent to hi@creativefabrica.com on 2026-09-17
# from x2newd@gmail.com. This job runs daily, computes days-since-send,
# and surfaces a warning when a follow-up is due — so nobody has to
# remember to check the inbox.

CF_EMAIL_SENT="2026-09-17"
CF_EXPECTED_RESPONSE_DAYS="5"
CF_FOLLOWUP_DAYS="7"

today=$(date -u +%F)
days_since=$(( ( $(date -d "$today" +%s) - $(date -d "$CF_EMAIL_SENT" +%s) ) / 86400 ))

echo "CF designer-approval tracker (autonomous monitor)"
echo "Email sent:   $CF_EMAIL_SENT"
echo "Today:        $today"
echo "Days since:   $days_since"
echo "Expected:     within $CF_EXPECTED_RESPONSE_DAYS business days"

if [ "$days_since" -ge "$CF_FOLLOWUP_DAYS" ]; then
  echo "::warning::CF designer approval follow-up due ($days_since days)."
  echo "::warning::Next: send follow-up email to hi@creativefabrica.com re: Account #30068942."
elif [ "$days_since" -gt "$CF_EXPECTED_RESPONSE_DAYS" ]; then
  echo "::warning::CF response window passed ($days_since days) without tracked reply."
else
  echo "Within expected response window. No action needed."
fi