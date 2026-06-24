#if !defined(INTEGRATION_H)
#define INTEGRATION_H

#include <complex>
#include <cmath>
#include <memory>
#include <gsl/gsl_math.h>
#include <gsl/gsl_monte.h>
#include <gsl/gsl_monte_vegas.h>
#include "callable.h"
#include "kinematics.h"
#include "group_g.h"

using namespace decay_widths;

template<class T>
struct Estimate {
    T value;
    T error;

    bool is_compatible(const Estimate<T> &other, int n_sigma=1) {
        if (this->value < other.value) {
            return this->value + n_sigma * this->error > other.value - n_sigma * other.error;
        } else {
            return this->value - n_sigma * this->error < other.value + n_sigma * other.error;
        }
    }
};

class Process {

public:
    
    Process(std::unique_ptr<Callable<complex_t, param_t>> &&f, std::unique_ptr<Kinematics> &&kinematics);
    Process(const std::string& f_name, std::unique_ptr<Kinematics> &&kinematics);
    Process(std::unique_ptr<Kinematics> &&kinematics);

    void set_function(const std::string& f_name);

    double operator()(const std::vector<double> &kin_args = {});

    bool initialized();

    Kinematics* get_kinematics();

private:
    std::unique_ptr<Callable<complex_t, param_t>> m_f;
    std::unique_ptr<Kinematics> m_kinematics;

};

class Integrator {

public:
    
    Integrator();
    Integrator(std::unique_ptr<Process> &&process);
    Integrator(Kinematics& kinematics);
    Integrator(const std::string& function, Kinematics& kinematics);

    void set_process(std::unique_ptr<Process> &&process);

    void set_function(const std::string& f_name);

    Kinematics* get_kinematics();

    void integrate();

    Estimate<double> get_integral() const;

    double get_integral_value() const;

    double get_integral_error() const;

    void set_calls_per_iter(size_t calls);

    void set_max_iter(size_t max_iter);

private:
    static constexpr size_t DEFAULT_CALLS_PER_ITER = 1000;
    static constexpr size_t DEFAULT_MAX_ITER = 50;

    std::unique_ptr<Process> m_proc;
    Estimate<double> m_integral;
    bool m_converged;
    gsl_monte_function m_monte_func;

    size_t m_calls_per_iter;
    size_t m_max_iter;

    static double func(double x[], size_t dim, void* par);

};

#endif // INTEGRATION_H
