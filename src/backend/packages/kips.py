# coding:utf-8
import pandas as pd

# ========================================
# KPI'S CHECKING
# ========================================
def check_kpis_value(
        df_op: pd.DataFrame,
        df_down: pd.DataFrame
    ):
    """
        Checking whether sum of SMU hours and Downtime hours don't
        exceed 744 hours for the month
        params:
            - df_op --> operating hours dataframe
            - df_down --> downtime hours dataframe
        return:
            - dataframe
    """

    down = (
        df_down.groupby(['Equip No', 'YearMonth', 'Model'], as_index=False, dropna=False)['DowntimeHours']
        .sum()
    )

    op = (
        df_op.groupby(['Equipment', 'YearMonth', 'Model'], as_index=False, dropna=False)['SMU Hours']
        .sum()
    )

    df_merge = op.merge(
        down,
        left_on='Equipment',
        right_on='Equip No',
        how='outer'
    )

    df_merge['Equipment'] = df_merge['Equipment'].fillna(df_merge['Equip No'])
    df_merge['YearMonth'] = df_merge['YearMonth_x'].fillna(df_merge['YearMonth_y'])
    df_merge['Model'] = df_merge['Model_x'].fillna(df_merge['Model_y'])

    df_merge = df_merge.drop(
        columns=['Equip No', 'Model_x', 'Model_y']
    )

    df_merge[['SMU Hours', 'DowntimeHours']] = (
        df_merge[['SMU Hours', 'DowntimeHours']]
        .fillna(0)
    )

    # Réorganiser les colonnes
    df_merge = df_merge[[
        'Equipment', 'YearMonth', 'Model', 'DowntimeHours', 'SMU Hours']]

    # Convertir en datetime (1er jour du mois)
    df_merge['YearMonth'] = pd.to_datetime(df_merge['YearMonth'], format='%Y-%m')

    df_merge['Used Hrs'] = df_merge['DowntimeHours'] + df_merge['SMU Hours']
    df_merge['Calendar Hrs'] = df_merge['YearMonth'].dt.days_in_month * 24

    return df_merge


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
