# coding:utf-8

import pandas as pd
import numpy as np

# ========================================
# KPI'S CHECKING
# ========================================
def check_kpis_value(
        df_op_hrs: pd.DataFrame,
        df_downtime_hrs: pd.DataFrame,
        month_hours= 744
    ):
    """
        Checking whether sum of SMU hours and Downtime hours don't
        exceed 744 hours for the month
        params:
            - df_op_hrs --> operating hours dataframe
            - df_downtime_hrs --> downtime hours dataframe
            - month_hours --> total hours in month
        return:
            - dataframe
    """

    df= df_op_hrs.copy()
    df_ = df_downtime_hrs.copy()

    df_ = df_.groupby('Equip No')['DowntimeHours'].sum()
    df_ = df_.reset_index()
    
    df = df[['Equipment', 'Model', 'SMU Hours']]
    df['DowntimeHours'] = df['Equipment'].map(df_.set_index(
        df_['Equip No'])['DowntimeHours']
    )

    df['Rest hours'] = (
        month_hours - (df['SMU Hours'] + df['DowntimeHours'])
    )

    return df


# ========================================
# FLEET PERFORMANCE
# ========================================
def mttr_equip():
    pass


def mtbs_equip():
    pass


def scheduled_downtime_percentage():
    pass


def availability_index():
    pass


def maintenance_ratio():
    pass


def top_problem_summary():
    pass


def asset_utilization():
    pass


# =============================================
# PREVENTIVE MAINTENANCE (Performance metrics)
# =============================================
def mtbs_pm():
    pass


def mttr_pm():
    pass


def unavailability_pm():
    pass


def service_accuracy():
    pass


def backlog_executed_pm():
    pass


def backlog_generated_pm():
    pass


# ==============================================
# CONDITION MONITORING
# ==============================================
def mtbf_equip():
    pass


def unavailability_no_pm():
    pass


# =============================================
# BACKLOG Mgt
# =============================================
def schedule_downtime_percentage():
    pass


# =============================================
# PLANNING AND SCHEDULING PERFORMANCE METRICS
# =============================================
def prtg_sch_downtime():
    pass


def sch_compliance_hrs():
    pass


def shc_compliance_event():
    pass


def pcr_sch():
    pass


# =============================================
# REPAIR Mgt PERFORMANCE METRICS
# =============================================
def mttr_shop():
    pass


def  mttr_field():
    pass


def mttr_shop_no_delay():
    pass


def mtbs_repair():
    pass


def prtg_redo():
    pass


def unavailability_delay():
    pass
