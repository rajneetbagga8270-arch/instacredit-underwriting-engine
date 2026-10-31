import streamlit as st
import pandas as pd
import numpy_financial as npf
import plotly.graph_objects as go

st.set_page_config(page_title="InstaCredit", page_icon="🏦", layout="wide")
st.title("🏦 InstaCredit: Retail Underwriting Engine")
st.caption("Automated lending simulator based on FOIR benchmarks and CIBIL risk pricing.")
st.divider()

# --- SIDEBAR INPUTS ---
st.sidebar.header("Applicant Profile")
monthly_income = st.sidebar.number_input("Net Monthly Income (₹)", min_value=15000, value=85000, step=5000)
existing_emi = st.sidebar.number_input("Existing Monthly Debt / EMIs (₹)", min_value=0, value=15000, step=2500)
cibil_score = st.sidebar.slider("CIBIL Credit Score", min_value=300, max_value=900, value=770, step=5)
employer_cat = st.sidebar.selectbox("Employer Category", ["Category A (Top MNCs/PSUs)", "Category B (Mid Corporates)", "Category C (Others)"])

st.sidebar.header("Requested Facility")
requested_loan = st.sidebar.number_input("Requested Loan Amount (₹)", min_value=50000, max_value=4000000, value=600000, step=50000)
tenure_years = st.sidebar.slider("Requested Tenure (Years)", min_value=1, max_value=7, value=3)
tenure_months = tenure_years * 12

def compute_risk_pricing(cibil, cat):
    if cibil < 700:
        return None
    base = 10.25 if cibil >= 800 else (11.25 if cibil >= 750 else 12.75)
    if "Category B" in cat:
        base += 0.50
    elif "Category C" in cat:
        base += 1.25
    return base

assigned_rate = compute_risk_pricing(cibil_score, employer_cat)

if assigned_rate is None:
    st.error("❌ Application Declined: CIBIL below 700 threshold.")
    st.caption("Applicants below 700 require secured credit alternatives or credit rehabilitation.")
else:
    foir_cap = 0.60 if monthly_income >= 60000 else 0.50
    max_total_emi = monthly_income * foir_cap
    max_available_emi = max_total_emi - existing_emi

    if max_available_emi <= 0:
        st.error("❌ Application Declined: Debt obligations exceed allowable FOIR.")
        st.caption(f"Current Debt-to-Income: {((existing_emi / monthly_income) * 100):.1f}% | Permissible Limit: {foir_cap * 100:.0f}%")
    else:
        monthly_r = (assigned_rate / 100) / 12
        max_sanction = npf.pv(monthly_r, tenure_months, -max_available_emi)
        sanctioned_loan = min(float(requested_loan), float(max_sanction))
        scheduled_emi = npf.pmt(monthly_r, tenure_months, -sanctioned_loan)
        resultant_foir = ((existing_emi + scheduled_emi) / monthly_income) * 100

        st.success("✅ Application Approved for Instant Disbursal")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Sanctioned Amount", f"₹{sanctioned_loan:,.0f}")
        k2.metric("Interest Rate", f"{assigned_rate:.2f}% p.a.")
        k3.metric("Monthly EMI", f"₹{scheduled_emi:,.0f}")
        k4.metric("FOIR Post-Disbursal", f"{resultant_foir:.1f}%")

        balance = sanctioned_loan
        records = []
        for m in range(1, tenure_months + 1):
            interest_part = balance * monthly_r
            principal_part = scheduled_emi - interest_part
            balance = max(0.0, balance - principal_part)
            records.append({"Month": m, "Principal": principal_part, "Interest": interest_part, "Balance": balance})
        df_amort = pd.DataFrame(records)

        st.subheader("📈 Debt Repayment Trajectory")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_amort["Month"], y=df_amort["Principal"], name="Principal Paid", marker_color="#003366"))
        fig.add_trace(go.Bar(x=df_amort["Month"], y=df_amort["Interest"], name="Interest Component", marker_color="#FF6F00"))
        fig.update_layout(barmode="stack", xaxis_title="Month", yaxis_title="Amount (₹)", height=400)
        st.plotly_chart(fig, use_container_width=True)

        sanction_memo = f"""
============================================================
              INSTACREDIT SANCTION LETTER
============================================================
Monthly Income (Net)    : INR {monthly_income:,.2f}
Applicant CIBIL Score   : {cibil_score}
Employer Category       : {employer_cat}

Sanctioned Facility     : INR {sanctioned_loan:,.2f}
Applicable Rate of Int. : {assigned_rate:.2f}% p.a.
Loan Repayment Period   : {tenure_months} Months
Monthly Repayment EMI   : INR {scheduled_emi:,.2f}

Consolidated FOIR       : {resultant_foir:.2f}%
============================================================
Ready for Instant Disbursal via Net Banking / iMobile
============================================================
"""
        st.download_button("📥 Download Sanction Letter", sanction_memo, file_name="sanction_memo.txt", mime="text/plain")