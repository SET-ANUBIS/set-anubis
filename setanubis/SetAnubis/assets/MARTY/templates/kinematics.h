#if !defined(KINEMATICS_H)
#define KINEMATICS_H

#include <cmath>
#include <vector>
#include <array>
#include <complex>
#include <memory>
#include <functional>
#include <utility>
#include "common.h"
#include "params.h"

using matrix_t = std::vector<std::vector<double>>;
using vector_t = std::vector<double>;
using namespace decay_widths;

class Momentum {

public:

    Momentum() : m_components(4), m_mass(0) {}
    Momentum(vector_t components);
    Momentum(double m, double p, const vector_t &dir);
    Momentum(double m);

    Momentum(Momentum&) = delete;
    Momentum& operator=(Momentum&) = delete;
    Momentum(Momentum&& other) noexcept;
    Momentum& operator=(Momentum&& other) noexcept;

    ~Momentum() = default;

    std::string to_string() const;

    double& operator[](std::size_t idx);
    double operator[](std::size_t idx) const;

    Momentum& operator+=(const Momentum& rhs);
    friend Momentum operator+(Momentum lhs, const Momentum& rhs);

    Momentum& operator-=(const Momentum& rhs);
    friend Momentum operator-(Momentum lhs, const Momentum& rhs);

    friend double operator*(const Momentum& lhs, const Momentum& rhs);

private:

    vector_t m_components;
    double m_mass;

};

class LorentzTransformation {

public:

    LorentzTransformation() : m_matrixRepresentation(4, vector_t(4)) {}
    LorentzTransformation(const matrix_t& components);

    virtual std::unique_ptr<LorentzTransformation> inverse() const;

    std::string to_string() const;

    void sanitize_zeros(double eps=1e-12); 

    vector_t& operator[](std::size_t idx);
    const vector_t& operator[](std::size_t idx) const;

    LorentzTransformation& operator*=(const LorentzTransformation& rhs);
    friend LorentzTransformation operator*(LorentzTransformation lhs, const LorentzTransformation& rhs);
    friend Momentum operator*(const LorentzTransformation& lhs, const Momentum& rhs);

protected:

    matrix_t m_matrixRepresentation;
    
};

class LorentzBoost : public LorentzTransformation {

public:

    LorentzBoost(const vector_t& beta);
    LorentzBoost(double gamma, int dir);
    LorentzBoost(const matrix_t& components);

    matrix_t buildMatrixRepresentation(); 

    std::unique_ptr<LorentzTransformation> inverse() const override;

    double get_gamma() const;
    double get_beta_sq() const;
    vector_t get_beta() const;

private:

    double m_gamma;
    vector_t m_beta;

};

class Rotation : public LorentzTransformation {

public:

    Rotation(double theta_x, double theta_y, double theta_z);
    Rotation(matrix_t components);

    matrix_t buildMatrixRepresentation(); 

    std::unique_ptr<LorentzTransformation> inverse() const override;

    vector_t get_angles();

private:

    double m_theta_x;
    double m_theta_y;
    double m_theta_z;
};

class KinematicsCalculator {

public:

    KinematicsCalculator(size_t incoming, size_t outgoing, const std::vector<double>& masses, double s, int ps_dim);

    virtual ~KinematicsCalculator() = default;
    virtual void compute_momenta(std::vector<double> kin_params) = 0;
    virtual std::vector<std::pair<double, double>> compute_kinematic_limits() const = 0;
    virtual double compute_phase_space_factor([[__maybe_unused__]] std::vector<double> kin_params) = 0;
    virtual void initialize_constants();

    virtual void set_mass(size_t idx, double m);

    void set_s(double s);
    
    const std::vector<Momentum>& get_momenta() const;
    const Momentum& get_momentum(size_t idx) const;

    double get_mass(size_t idx) const;
    const std::vector<double>& get_masses() const;

    int get_phase_space_dim() const;

protected:
    size_t m_incoming, m_outgoing;
    std::vector<double> m_masses;
    std::vector<double> m_masses_sq;
    std::vector<Momentum> m_momenta;
    double m_s;
    const int m_phase_space_dim;
    double m_phase_space_factor;

    double get_s_min() const;
};

class KinematicsCalculator12 : public KinematicsCalculator {
    /* 
    * phase space dim = 0
    * kin_params = []
    */
public:
    KinematicsCalculator12(const std::vector<double>& masses, double s): KinematicsCalculator(1, 2, masses, s, 0) { initialize_constants(); }
    void compute_momenta(std::vector<double> kin_params) override;
    std::vector<std::pair<double, double>> compute_kinematic_limits() const override;
    double compute_phase_space_factor(std::vector<double> kin_params) override;
    void set_mass(size_t idx, double m) override;
    void initialize_constants() override;

};

class KinematicsCalculator13 : public KinematicsCalculator {
    /* 
    * phase space dim = 2
    * kin_params = [x = p1.p2 / m1^2, y = p1.p3 / m1^2]
    */
public:
    KinematicsCalculator13(const std::vector<double>& masses, double s): KinematicsCalculator(1, 3, masses, s, 2) { initialize_constants(); }
    void compute_momenta(std::vector<double> kin_params) override;
    std::vector<std::pair<double, double>> compute_kinematic_limits() const override;
    double compute_phase_space_factor(std::vector<double> kin_params) override;
    void set_mass(size_t idx, double m) override;
    void initialize_constants() override;

private:
    const Rotation m_rot_pi {0, M_PI, 0};
    double m_glob_fact;
};

class KinematicsCalculator22 : public KinematicsCalculator {
    /* 
    * phase space dim = 1
    * kin_params = [theta = angle bt. p2 and p3]
    */
public:
    KinematicsCalculator22(const std::vector<double>& masses, double s) : KinematicsCalculator(2, 2, masses, s, 1) { initialize_constants(); }
    void compute_momenta(std::vector<double> kin_params) override;
    std::vector<std::pair<double, double>> compute_kinematic_limits() const override;
    double compute_phase_space_factor(std::vector<double> kin_params) override;
    void initialize_constants() override;

private:
    double m_p_out;
};

class KinematicsCalculator23 : public KinematicsCalculator {

public:
    KinematicsCalculator23(const std::vector<double>& masses, double s) : KinematicsCalculator(2, 3, masses, s, 4) { initialize_constants(); }
    void compute_momenta(std::vector<double> kin_params) override;
    std::vector<std::pair<double, double>> compute_kinematic_limits() const override;
    double compute_phase_space_factor(std::vector<double> kin_params) override;
    void initialize_constants() override;

private:
    double m_glob_fact;
};

// class KinematicsCalculator24 : public KinematicsCalculator {

// public:
//     KinematicsCalculator24(const std::vector<double>& masses, double s) : KinematicsCalculator(masses, s, 7) {}
//     void compute_momenta(std::vector<double> kin_params) override;
//     std::vector<std::pair<double, double>> compute_kinematic_limits() const override;
//     double compute_phase_space_factor(std::vector<double> kin_params) const override;
// };

class Kinematics {

public:

    Kinematics(const std::vector<double> &incoming_masses, const std::vector<double> &outgoing_masses, double sqrt_s, param_t *params);
    Kinematics(double incoming_mass, const std::vector<double> &outgoing_masses, param_t *params);
    Kinematics(size_t incoming, size_t outgoing, double sqrt_s, param_t *params);

    // Kinematics(const std::vector<std::string> &incoming_masses, const std::vector<std::string> &outgoing_masses, double sqrt_s, param_t* params);
    // Kinematics(std::string incoming_mass, const std::vector<std::string> &outgoing_masses, param_t *params);

    void update(const std::vector<double>& kin_params = {}, bool bypass_range_checks = false);

    void set_incoming_masses(const std::vector<double>& masses);

    void set_incoming_masses(double mass);

    void set_outgoing_masses(const std::vector<double>& masses);

    void set_masses(const std::vector<double>& incoming, const std::vector<double>& outgoing);

    void set_s(double sqrt_s);

    void set_ps_ind(std::function<bool(const std::vector<double>&, const std::vector<double>&)>& ps_ind);

    void reset_ps_ind();

    const Momentum& get_momentum(size_t id) const;

    double get_phase_space_factor(const std::vector<double>& kin_params = {});

    int get_phase_space_dim();

    std::vector<std::pair<double, double>> kin_limits() const;

    param_t get_params() const;
    
    bool is_point_valid(const std::vector<double> &kin_params);

    static double Beta(double x, double y, double z);
    static bool DEFAULT_PS_IND([[__maybe_unused__]] const std::vector<double>& kin_params, [[__maybe_unused__]] const std::vector<double>& masses) { return true; }
    static bool DEFAULT_PS_IND_13(const std::vector<double>& kin_params, const std::vector<double>& masses); 

private:
    size_t m_incoming, m_outgoing; 
    param_t *m_params;
    std::function<bool(const std::vector<double>&, const std::vector<double>&)> m_ps_ind;
    std::unique_ptr<KinematicsCalculator> m_calculator;

    bool check_kin(const std::vector<double>& kin_params) const;
};



#endif // KINEMATICS_H
