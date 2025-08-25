use super::errors::ExecError;
use super::models::Service;

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub enum Event {
    TaskStarted(&'static str), // plugin/task name
    TaskCompleted(&'static str),
    PortDiscovered(u16, String), // port, service name
    ServiceDiscovered(Service),
    TaskFailed(ExecError),
}
