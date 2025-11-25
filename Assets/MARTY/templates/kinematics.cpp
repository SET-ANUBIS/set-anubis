#include "kinematics.h"

double zero_if_close(double x, double eps=1e-10) {
    return std::abs(x) < eps ? 0 : x;
}

Momentum::Momentum(vector_t components) : m_components(components) {
    m_mass = std::sqrt(zero_if_close(*this * *this));
}

Momentum::Momentum(double m, double p, const vector_t &dir) : m_mass(m) {
    double norm_dir = std::sqrt(dir[0] * dir[0] + dir[1] * dir[1] + dir[2] * dir[2]);
    double E = std::sqrt(m * m + p * p);
    this->m_components = {E, dir[0] * p / norm_dir, dir[1] * p / norm_dir, dir[2] * p / norm_dir};
}

Momentum::Momentum(double m) : m_components({m, 0, 0, 0}), m_mass(m) {}

Momentum::Momentum(Momentum&& other) noexcept
    : m_components(std::move(other.m_components)), m_mass(other.m_mass) {
    other.m_mass = 0.;
}

Momentum& Momentum::operator=(Momentum&& other) noexcept {
    if (this != &other) {
        m_components = std::move(other.m_components);
        m_mass = other.m_mass;
        other.m_mass = 0.0;
    }
    return *this;
}

std::string Momentum::to_string() const {
    std::stringstream ss;
    ss << "[";
    for (auto &&p_i : m_components) {
        ss << p_i << "\t\n";
    }
    ss << "]";
    return ss.str();
}

double &Momentum::operator[](std::size_t idx)
{
    return m_components[idx];
}

double Momentum::operator[](std::size_t idx) const {
    return m_components[idx];
}

Momentum &Momentum::operator+=(const Momentum &rhs) {
    for (size_t i=0; i<this->m_components.size(); ++i)
        (*this)[i] += rhs[i];
    return *this;
}

Momentum &Momentum::operator-=(const Momentum &rhs) {
    for (size_t i=0; i<this->m_components.size(); ++i)
        (*this)[i] -= rhs[i];
    return *this;
}

Momentum operator+(Momentum lhs, const Momentum &rhs) {
    lhs += rhs;
    return lhs;
}

Momentum operator-(Momentum lhs, const Momentum &rhs) {
    lhs -= rhs;
    return lhs;
}

double operator*(const Momentum &lhs, const Momentum &rhs) {
    return lhs[0] * rhs[0] - lhs[1] * rhs[1] - lhs[2] * rhs[2] - lhs[3] * rhs[3]; 
}

LorentzTransformation::LorentzTransformation(const matrix_t& components) 
    : m_matrixRepresentation(std::move(components)) {
    this->sanitize_zeros();
}

// Not to be used !!
std::unique_ptr<LorentzTransformation> LorentzTransformation::inverse() const {
    return nullptr;
}

std::string LorentzTransformation::to_string() const {
    std::stringstream ss;
    ss << "[";
    for (size_t i = 0; i < 4; i++) {
        ss << (i == 0 ? "[" : " [");
        for (size_t j = 0; j < 4; j++) {
            ss << (*this)[i][j] << (j == 3 ? "" : "\t");
        }
        ss << (i == 3 ? "]" : "]\n");
    }
    ss << "]";
    return ss.str();
}

void LorentzTransformation::sanitize_zeros(double eps) {
    auto size = this->m_matrixRepresentation.size();
    for (size_t i = 0; i < size; i++) {
        for (size_t j = 0; j < size; j++) {
            this->m_matrixRepresentation[i][j] = zero_if_close(this->m_matrixRepresentation[i][j], eps);   
        }
    }
}

vector_t &LorentzTransformation::operator[](std::size_t idx) {
    return this->m_matrixRepresentation[idx];
}

const vector_t& LorentzTransformation::operator[](std::size_t idx) const {
    return this->m_matrixRepresentation[idx];
}

LorentzTransformation &LorentzTransformation::operator*=(const LorentzTransformation &rhs) {
    matrix_t this_copy = m_matrixRepresentation;
    size_t dim = this_copy.size();
    for (size_t i = 0; i < dim; i++) {
        for (size_t j = 0; j < dim; j++) {
            double Pij = 0;
            for (size_t k = 0; k < dim; k++) {
                Pij += this_copy[i][k] * rhs[k][j];
            }   
            this->m_matrixRepresentation[i][j] = Pij;
        }
    }
    sanitize_zeros();
    return *this;
}

LorentzTransformation operator*(LorentzTransformation lhs, const LorentzTransformation &rhs) {
    lhs *= rhs;
    return lhs;
}

LorentzBoost::LorentzBoost(const vector_t& beta) : m_beta(std::move(beta)) {
    double beta_sq = beta[0] * beta[0] + beta[1] * beta[1] + beta[2] * beta[2];
    m_gamma = 1 / std::sqrt(1 - beta_sq);
    buildMatrixRepresentation();
    sanitize_zeros();
}

LorentzBoost::LorentzBoost(double gamma, int dir) {
    double norm_beta = sqrt(1 - 1 / (gamma * gamma));
    vector_t beta = {0, 0, 0};
    beta[abs(dir) - 1] = dir * norm_beta / abs(dir);
    *this = LorentzBoost(beta);
}

LorentzBoost::LorentzBoost(const matrix_t& components) : LorentzTransformation(std::move(components)) {
    m_gamma = components[0][0];
    double bx = -components[0][1] / m_gamma;
    double by = -components[0][2] / m_gamma;
    double bz = -components[0][3] / m_gamma;
    m_beta = {bx, by, bz};
}

Momentum operator*(const LorentzTransformation &lhs, const Momentum &rhs) {
    auto inv_tsfo = lhs.inverse();
    vector_t t_momentum = {0, 0, 0, 0};
    for (size_t i = 0; i < 4; i++) {
        for (size_t j = 0; j < 4; j++) {
            t_momentum[i] += (*inv_tsfo)[j][i] * rhs[j];
        } 
    }
    return Momentum(t_momentum);
}

matrix_t LorentzBoost::buildMatrixRepresentation() {
    double g = m_gamma;
    double f = (g - 1) / (1 - 1 / (g * g));
    double bx = m_beta[0];
    double by = m_beta[1];
    double bz = m_beta[2];
    matrix_t matrep = 
    {
        {g      , -g * bx        , -g * by        , -g * bz        },
        {-g * bx, 1 + f * bx * bx, f * bx * by    , f * bx * bz    },
        {-g * by, f * by * bx    , 1 + f * by * by, f * by * bz    },
        {-g * bz, f * bz * bx    , f * bz * by    , 1 + f * bz * bz}
    };
    this->m_matrixRepresentation = matrep;
    return matrep;
}

std::unique_ptr<LorentzTransformation> LorentzBoost::inverse() const {
    vector_t new_beta {};
    for (double b : this->m_beta) {
        new_beta.emplace_back(-b);
    }
    return std::make_unique<LorentzBoost>(new_beta);
}

double LorentzBoost::get_gamma() const {
    return this->m_gamma;
}

double LorentzBoost::get_beta_sq() const {
    return 1 - 1 / std::pow(this->m_gamma, 2);
}

vector_t LorentzBoost::get_beta() const {
    return this->m_beta;
}

Rotation::Rotation(double theta_x, double theta_y, double theta_z) 
    : m_theta_x(theta_x), m_theta_y(theta_y), m_theta_z(theta_z) {
    buildMatrixRepresentation();
    sanitize_zeros();
}

Rotation::Rotation(matrix_t components) : LorentzTransformation(components) {
    m_theta_y = std::asin(-components[3][1]);
    if (components[3][1] == 1) {
        m_theta_z = 0;
        m_theta_x = std::acos(components[0][3]);
    } else if (components[3][1] == -1) {
        m_theta_z = 0;
        m_theta_x = std::acos(-components[0][3]);
    } else {
        m_theta_z = std::asin(components[2][1] / std::cos(m_theta_y));
        m_theta_x = std::asin(components[3][2] / std::cos(m_theta_y));
    }
}

matrix_t Rotation::buildMatrixRepresentation() {
    double cx = std::cos(m_theta_x);
    double cy = std::cos(m_theta_y);
    double cz = std::cos(m_theta_z);
    double sx = std::sin(m_theta_x);
    double sy = std::sin(m_theta_y);
    double sz = std::sin(m_theta_z);
    matrix_t matrep = 
    {
        {1, 0,       0                     , 0                     },
        {0, cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz},
        {0, cy * sz, sx * sy * sz + cx * cz, cx * sy * sz - sx * cz},
        {0, -sy    , sx * cy               , cx * cy}
    };
    this->m_matrixRepresentation = matrep;
    return matrep;
}

std::unique_ptr<LorentzTransformation> Rotation::inverse() const {
    matrix_t new_components = Rotation(0, 0, 0).buildMatrixRepresentation();
    for (size_t i = 0; i < new_components.size(); i++) {
        for (size_t j = 0; j < new_components[0].size(); j++) {   
            new_components[i][j] = (*this)[j][i];
        }
    }
    return std::make_unique<Rotation>(new_components);
}

vector_t Rotation::get_angles() {
    return vector_t {this->m_theta_x, this->m_theta_y, this->m_theta_z};
}

Kinematics::Kinematics(const std::vector<double> &incoming_masses, const std::vector<double> &outgoing_masses, double sqrt_s, param_t* params) {
    if (incoming_masses.size() < 1 || incoming_masses.size() > 2 
        || outgoing_masses.size() < 2 || outgoing_masses.size() > 3) {
        std::cerr << incoming_masses.size() << " > " << outgoing_masses.size() << " kinematics is not yet implemented." << std::endl;
        exit(123);
    }

    m_incoming = incoming_masses.size();
    m_outgoing = outgoing_masses.size();
    std::vector<double> masses;
    for (auto m : incoming_masses) {
        masses.emplace_back(m);
    }
    for (auto m : outgoing_masses) {
        masses.emplace_back(m);
    }

    reset_ps_ind();

    double s = sqrt_s * sqrt_s;
    if (m_incoming == 1 && m_outgoing == 2) {
        m_calculator = std::make_unique<KinematicsCalculator12>(masses, s);
    } else if (m_incoming == 1 && m_outgoing == 3) {
        m_ps_ind = Kinematics::DEFAULT_PS_IND_13;
        m_calculator = std::make_unique<KinematicsCalculator13>(masses, s);
    } else if (m_incoming == 2 && m_outgoing == 2) {
        m_calculator = std::make_unique<KinematicsCalculator22>(masses, s);
    } else if (m_incoming == 2 && m_outgoing == 3) {
        m_calculator = std::make_unique<KinematicsCalculator23>(masses, s);
    }
    
    m_params = params;
}

// Kinematics::Kinematics(const std::vector<std::string> &incoming_masses, const std::vector<std::string> &outgoing_masses, double sqrt_s, param_t* params) {
//     if (incoming_masses.size() < 1 || incoming_masses.size() > 2 
//         || outgoing_masses.size() < 2 || outgoing_masses.size() > 3) {
//         std::cerr << incoming_masses.size() << " > " << outgoing_masses.size() << " kinematics is not yet implemented." << std::endl;
//         exit(123);
//     }

//     m_incoming = incoming_masses.size();
//     m_outgoing = outgoing_masses.size();
//     std::vector<double> masses;
//     for (auto m : incoming_masses) {
//         masses.emplace_back(params->realParams.at(m));
//     }
//     for (auto m : outgoing_masses) {
//         masses.emplace_back(params->realParams.at(m));
//     }

//     reset_ps_ind();

//     double s = sqrt_s * sqrt_s;
//     if (m_incoming == 1 && m_outgoing == 2) {
//         m_calculator = std::make_unique<KinematicsCalculator12>(masses, s);
//     } else if (m_incoming == 1 && m_outgoing == 3) {
//         m_ps_ind = Kinematics::DEFAULT_PS_IND_13;
//         m_calculator = std::make_unique<KinematicsCalculator13>(masses, s);
//     } else if (m_incoming == 2 && m_outgoing == 2) {
//         m_calculator = std::make_unique<KinematicsCalculator22>(masses, s);
//     } else if (m_incoming == 2 && m_outgoing == 3) {
//         m_calculator = std::make_unique<KinematicsCalculator23>(masses, s);
//     }
    
//     m_params = params;
// }

// Kinematics::Kinematics(std::string incoming_mass, const std::vector<std::string> &outgoing_masses, param_t *params) {
//     std::vector<std::string> incoming_masses = {incoming_mass};

//     double sqrt_s = params->realParams.at(incoming_mass);
//     if (incoming_masses.size() < 1 || incoming_masses.size() > 2 
//         || outgoing_masses.size() < 2 || outgoing_masses.size() > 3) {
//         std::cerr << incoming_masses.size() << " > " << outgoing_masses.size() << " kinematics is not yet implemented." << std::endl;
//         exit(123);
//     }

//     m_incoming = incoming_masses.size();
//     m_outgoing = outgoing_masses.size();
//     std::vector<double> masses;
//     for (auto m : incoming_masses) {
//         masses.emplace_back(params->realParams.at(m));
//     }
//     for (auto m : outgoing_masses) {
//         masses.emplace_back(params->realParams.at(m));
//     }

//     reset_ps_ind();

//     double s = sqrt_s * sqrt_s;
//     if (m_incoming == 1 && m_outgoing == 2) {
//         m_calculator = std::make_unique<KinematicsCalculator12>(masses, s);
//     } else if (m_incoming == 1 && m_outgoing == 3) {
//         m_ps_ind = Kinematics::DEFAULT_PS_IND_13;
//         m_calculator = std::make_unique<KinematicsCalculator13>(masses, s);
//     } else if (m_incoming == 2 && m_outgoing == 2) {
//         m_calculator = std::make_unique<KinematicsCalculator22>(masses, s);
//     } else if (m_incoming == 2 && m_outgoing == 3) {
//         m_calculator = std::make_unique<KinematicsCalculator23>(masses, s);
//     }
    
//     m_params = params;

// }

Kinematics::Kinematics(double incoming_mass, const std::vector<double> &outgoing_masses, param_t *params) 
    : Kinematics({incoming_mass}, outgoing_masses, incoming_mass, params) {}

Kinematics::Kinematics(size_t incoming, size_t outgoing, double sqrt_s, param_t *params) 
    : Kinematics(std::vector<double>(incoming), std::vector<double>(outgoing), sqrt_s, params) {}

void Kinematics::update(const std::vector<double>& kin_params, bool bypass_range_checks) {
    if (!bypass_range_checks && !check_kin(kin_params)) {
        std::cerr << "Out of range kinetic parameters."  << std::endl;
        exit(123);
    }

    m_calculator->compute_momenta(kin_params);

    size_t n = m_incoming + m_outgoing;
    for (size_t i = 1; i <= n; i++) {
        for (size_t j = i + 1; j <= n; j++) {
            std::stringstream ss;
            ss << "s_" << i << j;
            if (m_params->realParams.contains(ss.str()))
                *(m_params->realParams[ss.str()]) = m_calculator->get_momentum(i - 1) * m_calculator->get_momentum(j - 1);
        }
    }
}

void Kinematics::set_incoming_masses(const std::vector<double> &masses) {
    if (masses.size() != m_incoming) {
        std::cerr << "Cannot change the kinematics type, only the mass values."  << std::endl;
        exit(123);
    }

    for (size_t i = 0; i < m_incoming; i++) {
        m_calculator->set_mass(i, masses.at(i));
    }
}

void Kinematics::set_incoming_masses(double mass) {
    set_incoming_masses(std::vector{mass});
}

void Kinematics::set_outgoing_masses(const std::vector<double> &masses) {
    if (masses.size() != m_outgoing) {
        std::cerr << "Cannot change the kinematics type, only the mass values."  << std::endl;
        exit(123);
    }

    for (size_t i = 0; i < m_outgoing; i++) {
        m_calculator->set_mass(m_incoming + i, masses.at(i));
    }
}

void Kinematics::set_masses(const std::vector<double> &incoming, const std::vector<double> &outgoing) {
    set_incoming_masses(incoming);
    set_outgoing_masses(outgoing);
}

void Kinematics::set_s(double sqrt_s) {
    m_calculator->set_s(sqrt_s * sqrt_s);
}

void Kinematics::set_ps_ind(std::function<bool(const std::vector<double>&, const std::vector<double>&)> &ps_ind) {
    m_ps_ind = ps_ind;
}

void Kinematics::reset_ps_ind() {
    m_ps_ind = Kinematics::DEFAULT_PS_IND;
}

void KinematicsCalculator::set_s(double s) {
    if (s < get_s_min()) {
        std::cerr << "CoM energy can't be lower than incoming or outgoing mass."  << std::endl;
        exit(123);
    }
    m_s = s;
    initialize_constants();
}

const Momentum& Kinematics::get_momentum(size_t idx) const {
    return m_calculator->get_momentum(idx);
}

double Kinematics::get_phase_space_factor(const std::vector<double>& kin_params) {
    return m_calculator->compute_phase_space_factor(kin_params);
}

int Kinematics::get_phase_space_dim() {
    return m_calculator->get_phase_space_dim();
}

bool Kinematics::check_kin(const std::vector<double> &kin_params) const {
    auto limits = kin_limits();

    if (kin_params.size() != limits.size())
        return false;

    for (size_t i = 0; i < limits.size(); i++) {
        if (limits[i].first > kin_params[i] || kin_params[i] > limits[i].second)
            return false;
    }
    
    return true;
}

std::vector<std::pair<double, double>> Kinematics::kin_limits() const {
    return m_calculator->compute_kinematic_limits();
}

param_t Kinematics::get_params() const {
    return *m_params;
}

bool Kinematics::is_point_valid(const std::vector<double> &kin_params) {
    return m_ps_ind(kin_params, m_calculator->get_masses());
}

bool Kinematics::DEFAULT_PS_IND_13(const std::vector<double> &kin_params, const std::vector<double>& masses) {
    std::vector<double> masses_sq;
    for (auto& m : masses)
        masses_sq.emplace_back(m * m);

    double t = masses_sq[0] * (1 - 2 * kin_params[0]) - masses_sq[1];
    double cos_s = (4 * masses_sq[0] * kin_params[1] * t - (t + masses_sq[2] - masses_sq[3]) * (t + masses_sq[0] - masses_sq[1])) 
                        / (masses_sq[0] * t * Beta(masses_sq[1], t, masses_sq[0]) * Beta(masses_sq[2], masses_sq[3], t));
    
    return (t > std::pow(masses[2] + masses[3], 2)) && (t < std::pow(masses[0] - masses[1], 2)) && (std::abs(cos_s) < 1);
}

KinematicsCalculator::KinematicsCalculator(size_t incoming, size_t outgoing, const std::vector<double>& masses, double s, int ps_dim) 
        : m_incoming(incoming), m_outgoing(outgoing), 
          m_masses(masses), m_masses_sq(incoming + outgoing), 
          m_momenta(incoming + outgoing),
          m_s(s), m_phase_space_dim(ps_dim), m_phase_space_factor(0) {}

double KinematicsCalculator::get_s_min() const {
    double mass_in = 0;
    for (size_t i = 0; i < m_incoming; i++) {
        mass_in += m_masses[i];
    }

    double mass_out = 0;
    for (size_t i = 0; i < m_outgoing; i++) {
        mass_in += m_masses[m_incoming + i];
    }

    return pow(mass_in > mass_out ? mass_in : mass_out, 2);
}

void KinematicsCalculator::initialize_constants() {
    for (size_t i = 0; i < m_masses.size(); i++) {
        m_masses_sq[i] = pow(m_masses[i], 2);
    }
}

void KinematicsCalculator::set_mass(size_t idx, double m) {
    m_masses[idx] = m;
    initialize_constants();
}

const std::vector<Momentum>& KinematicsCalculator::get_momenta() const {
    return m_momenta;
}

const Momentum& KinematicsCalculator::get_momentum(size_t idx) const {
    return m_momenta[idx];
}

double KinematicsCalculator::get_mass(size_t idx) const {
    return m_masses[idx];
}

const std::vector<double> &KinematicsCalculator::get_masses() const {
    return m_masses;
}

int KinematicsCalculator::get_phase_space_dim() const {
    return m_phase_space_dim;
}

double Kinematics::Beta(double x, double y, double z) {
    return std::sqrt(1 - 2 * (x + y) / z + std::pow((x - y) / z, 2));
}

void KinematicsCalculator12::compute_momenta(std::vector<double> kin_params) { (void) kin_params; }

std::vector<std::pair<double, double>> KinematicsCalculator12::compute_kinematic_limits() const {
    return {};
}

double KinematicsCalculator12::compute_phase_space_factor(std::vector<double> kin_params) {
    (void) kin_params;        
    return m_phase_space_factor;
}

void KinematicsCalculator12::set_mass(size_t idx, double m) {
    if (idx == 0) {
        m_s = m * m;
    }
    m_masses[idx] = m;
    initialize_constants();
}

void KinematicsCalculator12::initialize_constants() {
    KinematicsCalculator::initialize_constants();
    double m_1 = m_masses[0];
    double b23 = Kinematics::Beta(m_masses_sq[1], m_masses_sq[2], m_s);
    double p = m_1 * b23 / 2;
    m_momenta[0] = std::move(Momentum(m_1));
    m_momenta[1] = std::move(Momentum(m_masses[1], p, {0, 0, 1}));
    m_momenta[2] = std::move(Momentum(m_masses[2], p, {0, 0, -1}));
    m_phase_space_factor = b23 / (16 * M_PI * m_1);
}

void KinematicsCalculator13::compute_momenta(std::vector<double> kin_params) {
    double t = m_masses_sq[0] * (1 - 2 * kin_params[0]) - m_masses_sq[1];
    double cos_s = (4 * m_masses_sq[0] * kin_params[1] * t - (t + m_masses_sq[2] - m_masses_sq[3]) * (t + m_masses_sq[0] - m_masses_sq[1])) 
                        / (m_masses_sq[0] * t * Kinematics::Beta(m_masses_sq[1], t, m_masses_sq[0]) * Kinematics::Beta(m_masses_sq[2], m_masses_sq[3], t));
    double sin_s = sqrt(1 - cos_s * cos_s);
    double p = m_masses[0] * Kinematics::Beta(t, m_masses_sq[1], m_s) / 2;
    double p_star = std::sqrt(t) * Kinematics::Beta(m_masses_sq[2], m_masses_sq[3], t) / 2;
    double gamma = (m_masses_sq[0] + t - m_masses_sq[1]) / (2 * std::sqrt(t) * m_masses[0]);
    auto boost = LorentzBoost(gamma, 3);

    m_momenta[1] = std::move(Momentum(m_masses[1], p, vector_t {0, 0, 1}));
    m_momenta[2] = std::move(m_rot_pi * (boost * Momentum(m_masses[2], p_star, {sin_s, 0, cos_s})));
    m_momenta[3] = std::move(m_rot_pi * (boost * Momentum(m_masses[3], p_star, {-sin_s, 0, -cos_s})));
}

std::vector<std::pair<double, double>> KinematicsCalculator13::compute_kinematic_limits() const {
    double t_min = pow(m_masses[2] + m_masses[3], 2);
    double t_max = pow(m_masses[0] - m_masses[1], 2);
    double x_max = (m_masses_sq[0] - m_masses_sq[1] - t_min) / (2 * m_masses_sq[0]);
    double x_min = (m_masses_sq[0] - m_masses_sq[1] - t_max) / (2 * m_masses_sq[0]);

    double y_min, y_max;
    if (m_masses[2] == 0 && m_masses[3] == 0) {
        y_min = 0;
        y_max = (1 - m_masses_sq[1] / m_masses_sq[0]) / 2;
    } else if (m_masses[1] == 0 && m_masses[3] == 0) {
        y_min = m_masses[3] / m_masses[1];
        y_max = (1 + m_masses_sq[3] / m_masses_sq[1]) / 2;
    } else {
        double t_y_min = (m_masses[2] * (m_masses_sq[0] - m_masses_sq[1]) + m_masses[0] * (m_masses_sq[3] - m_masses_sq[2])) / (m_masses[0] - m_masses[2]);
        double t_y_max = (m_masses[3] * (m_masses_sq[0] - m_masses_sq[1]) + m_masses[1] * (m_masses_sq[2] - m_masses_sq[3])) / (m_masses[1] + m_masses[4]);
        y_min = (t_y_min + m_masses_sq[2] - m_masses_sq[3]) * (t_y_min + m_masses_sq[0] - m_masses_sq[1]) / (4 * t_y_min * m_masses_sq[0])
                            - Kinematics::Beta(m_masses_sq[1], t_y_min, m_masses_sq[0]) * Kinematics::Beta(m_masses_sq[2], m_masses_sq[3], t_y_min) / 4;
        y_max = (t_y_max + m_masses_sq[2] - m_masses_sq[3]) * (t_y_max + m_masses_sq[0] - m_masses_sq[1]) / (4 * t_y_max * m_masses_sq[0])
                            + Kinematics::Beta(m_masses_sq[1], t_y_max, m_masses_sq[0]) * Kinematics::Beta(m_masses_sq[2], m_masses_sq[3], t_y_max) / 4;
    }
    return {{0, 1}, {0, 1}}; //eheh TODO
    return {{x_min, x_max}, {y_min, y_max}};
}

double KinematicsCalculator13::compute_phase_space_factor(std::vector<double> kin_params) {
    return m_glob_fact;
}

void KinematicsCalculator13::set_mass(size_t idx, double m) {
    if (idx == 0) {
        m_s = m * m;
    }
    m_masses[idx] = m;
    initialize_constants();
}

void KinematicsCalculator13::initialize_constants() {
    KinematicsCalculator::initialize_constants();
    m_momenta[0] = std::move(Momentum(m_masses[0]));
    m_glob_fact = m_masses[0] / (8 * pow(2 * M_PI, 3));
}

void KinematicsCalculator22::compute_momenta(std::vector<double> kin_params) {
    double c = kin_params[0];
    double s = sqrt(1 - c * c);

    m_momenta[2] = std::move(Momentum(m_masses[2], m_p_out, {s, 0, c}));
    m_momenta[3] = std::move(Momentum(m_masses[3], m_p_out, {-s, 0, -c}));
}

std::vector<std::pair<double, double>> KinematicsCalculator22::compute_kinematic_limits() const {
    return {{-1, 1}};
}

double KinematicsCalculator22::compute_phase_space_factor(std::vector<double> kin_params) {
    (void) kin_params;
    return m_phase_space_factor;
}

void KinematicsCalculator22::initialize_constants() {
    KinematicsCalculator::initialize_constants();
    double b12 = Kinematics::Beta(m_masses_sq[0], m_masses_sq[1], m_s);
    double b34 = Kinematics::Beta(m_masses_sq[2], m_masses_sq[3], m_s);
    double p_in = std::sqrt(m_s) * b12 / 2;
    m_p_out = std::sqrt(m_s) * b34 / 2;
    m_momenta[0] = std::move(Momentum(m_masses[0], p_in, {0, 0, 1}));
    m_momenta[1] = std::move(Momentum(m_masses[1], p_in, {0, 0, -1}));
    m_phase_space_factor = b34 / (32 * M_PI * m_s * b12);
}

void KinematicsCalculator23::compute_momenta(std::vector<double> kin_params) {
    double t         = kin_params[0];
    double c_theta   = kin_params[1];
    double s_theta   = sqrt(1 - c_theta * c_theta);
    double c_theta_s = kin_params[2];
    double s_theta_s = sqrt(1 - c_theta_s * c_theta_s);
    double phi_s     = kin_params[3];

    double p      = std::sqrt(m_s) * Kinematics::Beta(t, m_masses_sq[2], m_s) / 2;
    double p_star = std::sqrt(t) * Kinematics::Beta(m_masses_sq[3], m_masses_sq[4], t) / 2;
    double gamma = (m_s + t - m_masses_sq[2]) / (2 * std::sqrt(m_s * t));
    auto boost = LorentzBoost(gamma, 3);
    auto rot = Rotation(0, M_PI + acos(c_theta), 0);

    m_momenta[2] = std::move(Momentum(m_masses[2], p, vector_t {s_theta, 0, c_theta}));
    m_momenta[3] = std::move(rot * (boost * Momentum(m_masses[3], p_star, {s_theta_s * cos(phi_s), s_theta_s * sin(phi_s), c_theta_s})));
    m_momenta[4] = std::move(rot * (boost * Momentum(m_masses[4], p_star, {-s_theta_s * cos(phi_s), -s_theta_s * sin(phi_s), -c_theta_s})));
}

std::vector<std::pair<double, double>> KinematicsCalculator23::compute_kinematic_limits() const {
    double t_min = pow(m_masses[3] + m_masses[4], 2);
    double t_max = pow(sqrt(m_s) - m_masses[2], 2);

    return {{t_min, t_max}, {-1, 1}, {-1, 1}, {0, 2 * M_PI}};
}

double KinematicsCalculator23::compute_phase_space_factor(std::vector<double> kin_params) {
    double b3 = Kinematics::Beta(kin_params[0], m_masses_sq[2], m_s);
    double b45 = Kinematics::Beta(m_masses_sq[3], m_masses_sq[4], kin_params[0]);
    return b3 * b45 * m_glob_fact;
}

void KinematicsCalculator23::initialize_constants() {
    KinematicsCalculator::initialize_constants();
    double b12 = Kinematics::Beta(m_masses_sq[0], m_masses_sq[1], m_s);
    double p_in   = std::sqrt(m_s) * b12 / 2;
    m_momenta[0] = std::move(Momentum(m_masses[0], p_in, {0, 0, 1}));
    m_momenta[1] = std::move(Momentum(m_masses[1], p_in, {0, 0, -1}));
    m_glob_fact = 1 / (128 * pow(2 * M_PI, 4) * m_s * b12);
}

// void KinematicsCalculator24::compute_momenta(std::vector<double> kin_params) {
//     double m_1 = m_masses[0];
//     double m_2 = m_masses[1];
//     double m_3 = m_masses[2];
//     double m_4 = m_masses[3];
//     double m_5 = m_masses[4];
//     double m_6 = m_masses[5];
//     double t_34         = kin_params[0];
//     double t_56         = kin_params[1];
//     double theta        = kin_params[2];
//     double theta_s_34   = kin_params[3];
//     double phi_s_34     = kin_params[4];
//     double theta_s_56   = kin_params[5];
//     double phi_s_56     = kin_params[6];

//     double p_12   = std::sqrt(m_s) * Beta(m_1 * m_1, m_2 * m_2, m_s) / 2;
//     double p_xy   = std::sqrt(m_s) * Beta(t_34, t_56, m_s) / 2;
//     double p_34   = std::sqrt(t_34) * Beta(m_3 * m_3, m_4 * m_4, t_34) / 2;
//     double p_56   = std::sqrt(t_56) * Beta(m_5 * m_5, m_6 * m_6, t_56) / 2;
//     double gamma_34 = sqrt(1 + p_xy * p_xy / t_34);
//     double gamma_56 = sqrt(1 + p_xy * p_xy / t_56);
//     auto boost_34 = LorentzBoost(gamma_34, -3);
//     auto rot_34 = Rotation(0, theta, 0);
//     auto boost_56 = LorentzBoost(gamma_56, 3);
//     auto rot_56 = Rotation(0, M_PI + theta, 0);

//     m_momenta[0] = Momentum(m_1, p_12, {0, 0, 1});
//     m_momenta[1] = Momentum(m_2, p_12, {0, 0, -1});
//     m_momenta[2] = rot_34 * (boost_34 * Momentum(m_3, p_34, {sin(theta_s_34) * cos(phi_s_34), sin(theta_s_34) * sin(phi_s_34), cos(theta_s_34)}));
//     m_momenta[3] = rot_34 * (boost_34 * Momentum(m_4, p_34, {-sin(theta_s_34) * cos(phi_s_34), -sin(theta_s_34) * sin(phi_s_34), -cos(theta_s_34)}));
//     m_momenta[4] = rot_56 * (boost_56 * Momentum(m_5, p_56, {sin(theta_s_56) * cos(phi_s_56), sin(theta_s_56) * sin(phi_s_56), cos(theta_s_56)}));
//     m_momenta[5] = rot_56 * (boost_56 * Momentum(m_6, p_56, {-sin(theta_s_56) * cos(phi_s_56), -sin(theta_s_56) * sin(phi_s_56), -cos(theta_s_56)}));
// }
