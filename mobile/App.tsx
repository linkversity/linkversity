import React, { useEffect, useCallback } from 'react';
import { AppNavigator, navigationRef } from './src/navigation/AppNavigator';
import ShareMenu, { ShareMenuData } from 'react-native-share-menu';
import { useAuthStore } from './src/store/useAuthStore';
import { Alert } from 'react-native';

const App = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const handleShare = useCallback((item: ShareMenuData) => {
    if (!item || !item.data) return;

    // item.data could be a URL or text containing a URL
    let url = '';
    if (typeof item.data === 'string') {
      const urlRegex = /(https?:\/\/[^\s]+)/g;
      const matches = item.data.match(urlRegex);
      url = matches ? matches[0] : item.data;
    } else if (Array.isArray(item.data)) {
        // Handle array of data if necessary
        url = item.data[0]?.data || '';
    }

    if (!url) return;

    if (!isAuthenticated) {
      Alert.alert('Linkversity', 'Please login to save links');
      return;
    }

    // Try to navigate if navigation is ready
    if (navigationRef && navigationRef.isReady()) {
      navigationRef.navigate('SaveLink', { url });
    } else {
        // Navigation not ready yet, we might need to store it and navigate later
        // or just wait for the screen to handle it via initial data
    }
  }, [isAuthenticated]);

  useEffect(() => {
    ShareMenu.getInitialShare(handleShare);
    const listener = ShareMenu.addNewShareListener(handleShare);

    return () => {
      listener.remove();
    };
  }, [handleShare]);

  return <AppNavigator />;
};

export default App;
