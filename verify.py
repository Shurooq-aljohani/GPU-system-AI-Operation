import json
import os

def verify():
    if not os.path.exists("kv_sim_report.json"):
        print("❌ FAIL: kv_sim_report.json not found.")
        return
        
    with open("kv_sim_report.json", "r") as f:
        report = json.load(f)
        
    slab_res = report["slab"]["peak_concurrent"]
    bp_res = report["blockpool"]["peak_concurrent"]
    adv = report["blockpool_advantage"]
    
    if adv > 3.0 and report["blockpool"]["rejected"] == 0:
        print(f"Extra Lab: reference: slab {slab_res} resident, block-pool {bp_res} resident, advantage {adv}x GREEN CHECK: PASS")
    else:
        print("❌ FAIL: Results do not match expected output.")

if __name__ == "__main__":
    verify()
