import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Image,
} from 'react-native';
import { useAuthStore } from '../store/useAuthStore';
import { apiClient } from '../api/client';

const logo = require('../assets/logo.png');

const LoginScreen = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const setAuth = useAuthStore((state) => state.setAuth);

  const handleLogin = async () => {
    if (!username || !password) {
      Alert.alert('Error', 'Please enter both username and password');
      return;
    }

    setLoading(true);
    const loginUrl = (apiClient.defaults.baseURL || '') + '/auth/api/login';
    console.log('--- [DEBUG] LOGIN ATTEMPT ---');
    console.log('DESTINATION:', loginUrl);
    console.log('PAYLOAD:', { username, password });

    try {
      const response = await apiClient.post('/auth/api/login', {
        username,
        password,
      });

      console.log('--- [DEBUG] LOGIN SUCCESS ---');
      console.log('STATUS:', response.status);
      console.log('RESPONSE:', JSON.stringify(response.data, null, 2));

      const { token, user } = response.data;
      setAuth(token, user);
    } catch (error: any) {
      console.log('--- [DEBUG] LOGIN FAILURE ---');
      if (error.response) {
        console.log('STATUS:', error.response.status);
        console.log('RESPONSE:', JSON.stringify(error.response.data, null, 2));
      } else {
        console.log('ERROR:', error.message);
      }
      
      const message = error.response?.data?.message || 'Failed to login';
      Alert.alert('Login Error', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Image source={logo} style={styles.logo} resizeMode="contain" />
        <Text style={styles.title}>Linkversity</Text>
        <Text style={styles.subtitle}>Save and organize your links</Text>
      </View>

      <View style={styles.form}>
        <TextInput
          style={styles.input}
          placeholder="Username"
          value={username}
          onChangeText={setUsername}
          autoCapitalize="none"
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          style={styles.button}
          onPress={handleLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Login</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 20,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logo: {
    width: 100,
    height: 100,
    marginBottom: 16,
  },
  title: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#ff8080', // Coral from web theme
    letterSpacing: -1,
  },
  subtitle: {
    fontSize: 16,
    color: '#475569',
    marginTop: 4,
    fontWeight: '500',
  },
  form: {
    gap: 16,
  },
  input: {
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 16,
    borderRadius: 12,
    fontSize: 16,
    color: '#1e293b', // Explicit dark text color
  },
  button: {
    backgroundColor: '#ff8080', // Coral button
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 8,
    shadowColor: '#ff8080',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default LoginScreen;
