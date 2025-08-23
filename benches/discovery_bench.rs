use criterion::{criterion_group, criterion_main, Criterion};

fn discovery_benchmarks(_c: &mut Criterion) {
    // TODO: Implement when crate structure allows it
}

fn memory_benchmarks(_c: &mut Criterion) {
    // TODO: Implement when crate structure allows it
}

criterion_group!(benches, discovery_benchmarks, memory_benchmarks);
criterion_main!(benches);