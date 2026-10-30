import sys
import os
import time

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.bin import Dustbin
from app.models.settings import EmailSetting
from app.email.alert_manager import AlertManager

def run_tests():
    print("==================================================")
    print("RUNNING ALERT LOGIC VERIFICATION TESTS")
    print("==================================================")

    db = SessionLocal()
    try:
        # Create an isolated AlertManager instance
        mgr = AlertManager()
        
        # Ensure email settings has 15 minute cooldown
        email_settings = db.query(EmailSetting).first()
        if not email_settings:
            email_settings = EmailSetting(cooldown_minutes=15)
            db.add(email_settings)
            db.commit()
            db.refresh(email_settings)
        else:
            email_settings.cooldown_minutes = 15
            db.commit()

        # Create or fetch a test dustbin
        test_bin = db.query(Dustbin).filter(Dustbin.bin_id == "TEST-BIN-01").first()
        if not test_bin:
            test_bin = Dustbin(
                bin_id="TEST-BIN-01",
                name="Cafeteria Bin",
                location="Building 2 Dining Hall",
                threshold=85.0,
                floor_litter_enabled=True,
                active=True
            )
            db.add(test_bin)
            db.commit()
            db.refresh(test_bin)

        bin_id = test_bin.id

        # --- Test 1: Normal fill (< 85%) and no overflow -> No email sent ---
        print("\n[Test 1] Normal fill (40%), no overflow:")
        res = mgr.process_bin_reading(db, test_bin, fill_percentage=40.0, floor_litter_detected=False)
        assert res is None, f"Expected None, got {res}"
        assert mgr.bin_state.get(bin_id) == "NORMAL" or bin_id not in mgr.bin_state
        print("[OK] Passed: No alert sent for normal fill.")

        # --- Test 2: Threshold breached (88% >= 85%) -> Immediate Initial Alert ---
        print("\n[Test 2] Threshold reached (88% >= 85%):")
        res = mgr.process_bin_reading(db, test_bin, fill_percentage=88.0, floor_litter_detected=False)
        assert res is not None, "Expected alert to trigger"
        assert res["alert_triggered"] is True
        assert res["is_recurring"] is False
        assert mgr.bin_state[bin_id] == "CRITICAL"
        print(f"[OK] Passed: Immediate alert sent. Reason: '{res['reason']}', State: CRITICAL")

        # --- Test 3: Still full (89%), 2 minutes later -> No email sent (cooldown active) ---
        print("\n[Test 3] 2 minutes later, still full (89%):")
        # Simulate time 2 minutes after first alert
        first_alert_ts = mgr.last_alert_time[bin_id]
        now_mock = first_alert_ts + 120  # 2 minutes later
        import app.email.alert_manager as am_mod
        original_time = am_mod.time.time
        am_mod.time.time = lambda: now_mock

        res = mgr.process_bin_reading(db, test_bin, fill_percentage=89.0, floor_litter_detected=False)
        assert res is None, f"Expected None during cooldown, got {res}"
        print("[OK] Passed: Cooldown active, no spam email sent.")

        # --- Test 4: Still full (89%), 15 minutes later -> Recurring alert triggered ---
        print("\n[Test 4] 15.5 minutes later, still not emptied (89%):")
        now_mock = first_alert_ts + (15.5 * 60)  # 15.5 minutes later
        res = mgr.process_bin_reading(db, test_bin, fill_percentage=89.0, floor_litter_detected=False)
        assert res is not None, "Expected recurring alert after 15 min"
        assert res["alert_triggered"] is True
        assert res["is_recurring"] is True
        print(f"[OK] Passed: Recurring alert sent. Reason: '{res['reason']}'")

        # --- Test 5: Bin is emptied (fill drops to 15%) -> State resets to NORMAL, emails STOP ---
        print("\n[Test 5] Bin is emptied (fill drops to 15%, no overflow):")
        now_mock = first_alert_ts + (20 * 60)
        res = mgr.process_bin_reading(db, test_bin, fill_percentage=15.0, floor_litter_detected=False)
        assert res is None, f"Expected None when emptied, got {res}"
        assert mgr.bin_state[bin_id] == "NORMAL", f"Expected NORMAL state, got {mgr.bin_state[bin_id]}"
        print("[OK] Passed: Bin marked as emptied. State reset to NORMAL. Emails stopped.")

        # --- Test 6: 15 minutes after emptied -> Still NO email sent! ---
        print("\n[Test 6] 15 minutes after being emptied (fill remains 15%):")
        now_mock = first_alert_ts + (35 * 60)
        res = mgr.process_bin_reading(db, test_bin, fill_percentage=15.0, floor_litter_detected=False)
        assert res is None, f"Expected None while empty, got {res}"
        print("[OK] Passed: No email sent while bin is empty. Recurring alerts stayed stopped.")

        # --- Test 7: Fill level normal (45%) BUT floor litter / overflow detected -> Immediate alert! ---
        print("\n[Test 7] Low fill (45%) but garbage overflow / floor litter detected:")
        now_mock = first_alert_ts + (40 * 60)
        res = mgr.process_bin_reading(db, test_bin, fill_percentage=45.0, floor_litter_detected=True)
        assert res is not None, "Expected alert on overflow"
        assert res["alert_triggered"] is True
        assert "overflow" in res["reason"].lower() or "litter" in res["reason"].lower()
        assert mgr.bin_state[bin_id] == "CRITICAL"
        print(f"[OK] Passed: Overflow triggered immediate alert. Reason: '{res['reason']}'")

        # --- Test 8: Overflow cleaned up and fill normal -> Resets to NORMAL ---
        print("\n[Test 8] Overflow cleaned up (floor litter cleared, fill 45%):")
        now_mock = first_alert_ts + (45 * 60)
        res = mgr.process_bin_reading(db, test_bin, fill_percentage=45.0, floor_litter_detected=False)
        assert res is None
        assert mgr.bin_state[bin_id] == "NORMAL"
        print("[OK] Passed: Cleaned up. State reset to NORMAL. Emails stopped.")

        # Restore original time function
        am_mod.time.time = original_time

        print("\n==================================================")
        print("ALL 8 VERIFICATION TESTS PASSED SUCCESSFULLY! 100% OK")
        print("==================================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
