export type DashboardMetric = {
  label: string;
  value: string;
  note: string;
};

export type TaskStep = {
  name: string;
  status: "未运行" | "运行中" | "成功" | "失败";
};
