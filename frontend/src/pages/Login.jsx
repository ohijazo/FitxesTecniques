import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

function Login({ onLogin }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.login(email, password);
      localStorage.setItem('token', data.token);
      localStorage.setItem('usuari', JSON.stringify(data.usuari));
      onLogin(data.usuari);
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <div style={{
          width: '56px', height: '56px', background: 'var(--brand)', borderRadius: '14px',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem',
          boxShadow: 'var(--shadow-md)'
        }}>
          <span style={{ color: '#fff', fontSize: '1.5rem', fontWeight: 700 }}>FC</span>
        </div>
        <h2>Fitxes Tècniques</h2>
        <p>Farinera Coromina — Inicia sessió per continuar</p>
      </div>

      {error && (
        <div style={{
          background: 'var(--danger-bg)', color: 'var(--danger)', padding: '0.6rem 1rem',
          borderRadius: 'var(--radius)', fontSize: '0.88rem', marginBottom: '1rem', textAlign: 'center'
        }}>
          {error}
        </div>
      )}

      <div className="card">
        <form onSubmit={handleSubmit}>
          <label>
            Correu electrònic
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus
              placeholder="nom@farineracoromina.com" />
          </label>
          <label>
            Contrasenya
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              placeholder="La teva contrasenya" />
          </label>
          <button type="submit" aria-busy={loading} disabled={loading}
            style={{ width: '100%', marginTop: '0.5rem', padding: '0.7rem' }}>
            {loading ? 'Entrant...' : 'Iniciar sessió'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
