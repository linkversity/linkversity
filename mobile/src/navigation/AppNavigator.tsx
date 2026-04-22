import React from 'react';
import { NavigationContainer, createNavigationContainerRef } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuthStore } from '../store/useAuthStore';

import LoginScreen from '../screens/LoginScreen';
import HomeScreen from '../screens/HomeScreen';
import SaveLinkScreen from '../screens/SaveLinkScreen';

export type RootStackParamList = {
  Login: undefined;
  Home: undefined;
  SaveLink: { url: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export const navigationRef = createNavigationContainerRef<RootStackParamList>();

export const AppNavigator = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <NavigationContainer ref={navigationRef}>
      <Stack.Navigator>
        {!isAuthenticated ? (
          <Stack.Screen 
            name="Login" 
            component={LoginScreen} 
            options={{ headerShown: false }}
          />
        ) : (
          <>
            <Stack.Screen name="Home" component={HomeScreen} />
            <Stack.Screen name="SaveLink" component={SaveLinkScreen} options={{ title: 'Save Link' }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};
