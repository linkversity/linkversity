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
    fontSize: 32,
    fontWeight: 'bold',
    color: '#2563eb',
  },
  subtitle: {
    fontSize: 16,
    color: '#64748b',
    marginTop: 8,
  },
  form: {
    gap: 16,
  },
  input: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 12,
    borderRadius: 8,
    fontSize: 16,
  },
  button: {
    backgroundColor: '#2563eb',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default LoginScreen;
