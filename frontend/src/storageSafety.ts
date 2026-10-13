export type SchedulerStatus={
  storage_failure:{id:string;kind:string;message:string;durable:false}|null;
  active:{id:string;kind:string}|null;
  reservation:string|null;
};

// Never infer release from a stale durable status, missing fields or a read error.
export function storageFailureReleased(status:SchedulerStatus):boolean{
  return !!status?.storage_failure&&status.active===null&&status.reservation===null;
}
