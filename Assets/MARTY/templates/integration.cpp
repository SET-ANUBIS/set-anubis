#include "integration.h"

Process::Process(std::unique_ptr<Callable<complex_t, param_t>> &&f, std::unique_ptr<Kinematics> &&kinematics) 
    : m_f(std::move(f)), m_kinematics(std::move(kinematics)) {}

Process::Process(const std::string& f_name, std::unique_ptr<Kinematics> &&kinematics) : m_kinematics(std::move(kinematics)) {
    set_function(f_name);
}

Process::Process(std::unique_ptr<Kinematics> &&kinematics) : m_kinematics(std::move(kinematics)) {
    m_f = nullptr;
}

void Process::set_function(const std::string &f_name) {
    m_f = std::make_unique<Callable<complex_t, param_t>>(fmap_G.at(f_name));
}

double Process::operator()(const std::vector<double>& kin_args) {
    m_kinematics->update(std::move(kin_args), true);
    if (m_kinematics->is_point_valid(kin_args)) {
        complex_t res = m_kinematics->get_phase_space_factor(kin_args) * (*m_f)(m_kinematics->get_params());
        if (abs(res.imag() / res.real()) > 1e-10) 
            std::cout << "Warning: Function evaluation yielded nonzero imaginary part. Check results." << std::endl;
        return res.real();
    } else {
        return 0;
    }
}

bool Process::initialized() {
    return m_kinematics && m_f;
}

Kinematics *Process::get_kinematics() {
    return m_kinematics.get();
}

Integrator::Integrator() {
    m_monte_func.f = &func;
    m_calls_per_iter = Integrator::DEFAULT_CALLS_PER_ITER;
    m_max_iter = Integrator::DEFAULT_MAX_ITER;
}

Integrator::Integrator(std::unique_ptr<Process> &&process) : Integrator() {
    set_process(std::move(process));
}

Integrator::Integrator(Kinematics &kinematics) 
: Integrator(std::make_unique<Process>(std::make_unique<Kinematics>(std::move(kinematics)))) {}

Integrator::Integrator(const std::string &function, Kinematics &kinematics) 
: Integrator(std::make_unique<Process>(function, std::make_unique<Kinematics>(std::move(kinematics)))) 
{}

void Integrator::set_process(std::unique_ptr<Process> &&process) {
    m_proc = std::move(process);
    m_converged = false;
    m_integral = {0, 0};
    m_monte_func.dim = m_proc->get_kinematics()->get_phase_space_dim();
    m_monte_func.params = m_proc.get();
}

void Integrator::set_function(const std::string &f_name) {
    m_proc->set_function(f_name);
    m_converged = false;
}

Kinematics *Integrator::get_kinematics() {
    return m_proc->get_kinematics();
}

void Integrator::integrate() {
    if (!m_proc->initialized()) {
        std::cerr << "Process to integrate is not fully initialized.\n";
        exit(123);
    }

    double res, err;
    size_t iter {0};
    const auto bounds = m_proc->get_kinematics()->kin_limits();
    const size_t dim = m_proc->get_kinematics()->get_phase_space_dim();

    if (dim == 0) {
        m_integral.value = (*m_proc)();
        m_integral.error = 0;
        m_converged = true;
        return;
    }

    std::vector<double> xl, xu;
    for (auto &&p : bounds) {
        xl.emplace_back(p.first);
        xu.emplace_back(p.second);
    }

    const gsl_rng_type *T;
    gsl_rng *r;
    gsl_rng_env_setup();

    T = gsl_rng_default;
    r = gsl_rng_alloc(T);

    gsl_monte_vegas_state *s = gsl_monte_vegas_alloc (dim);

    gsl_monte_vegas_integrate (&m_monte_func, &xl[0], &xu[0], dim, m_calls_per_iter / 10, r, s, &res, &err);
    do {
        gsl_monte_vegas_integrate (&m_monte_func, &xl[0], &xu[0], dim, m_calls_per_iter, r, s, &res, &err);
        ++iter;
    } while (abs(gsl_monte_vegas_chisq(s) - 1) > 0.4 && iter < m_max_iter);
    gsl_monte_vegas_free (s);

    if (iter == m_max_iter) {
        std::cout << "Maximum number of iterations reached. Integrator counldn't converge." << std::endl;
        m_converged = false;
    } else {
        m_converged = true;
        m_integral.value = res;
        m_integral.error = err;
    }
}

Estimate<double> Integrator::get_integral() const {
    if (!m_converged) {
        std::cerr << "Integral has not been evaluated or evaluation has not converged."  << std::endl;
        exit(123);
    }
    return m_integral;
}

double Integrator::get_integral_value() const {
    if (!m_converged) {
        std::cerr << "Integral has not been evaluated or evaluation has not converged."  << std::endl;
        exit(123);
    }
    return m_integral.value;
}

double Integrator::get_integral_error() const {
    if (!m_converged) {
        std::cerr << "Integral has not been evaluated or evaluation has not converged."  << std::endl;
        exit(123);
    }
    return m_integral.error;
}

void Integrator::set_calls_per_iter(size_t calls) {
    m_calls_per_iter = calls;
}

void Integrator::set_max_iter(size_t max_iter) {
    m_max_iter = max_iter;
}

double Integrator::func(double x[], size_t dim, void *par) {
    std::vector<double> kin_p(x, x + dim);
    Process* proc = (Process*) par;
    return (*proc)(kin_p);
}
