use super::models::Service;
use super::errors::ExecError;

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub enum Event {
    TaskStarted(&'static str),   // plugin/task name
    TaskCompleted(&'static str),
    PortDiscovered(u16, String), // port, service name
    ServiceDiscovered(Service),
    TaskFailed(ExecError),
}