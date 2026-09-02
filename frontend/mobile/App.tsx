import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { initConfig } from '../shared/services/config';
import { HomeScreen } from './src/screens/HomeScreen';
import { RoutesScreen } from './src/screens/RoutesScreen';
import { SavedScreen } from './src/screens/SavedScreen';
import { ProfileScreen } from './src/screens/ProfileScreen';

// Initialise shared config for mobile
initConfig({
  // NOTE: "localhost" only reaches a backend running on this same device.
  // For the Android emulator use 10.0.2.2 instead of localhost; for a
  // physical device or iOS simulator on the same network, use the dev
  // machine's LAN IP (e.g. http://192.168.x.x:8000/api/v1).
  apiUrl: 'http://localhost:8000/api/v1',
  useMockData: false,
});

const Tab = createBottomTabNavigator();

export default function App() {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <StatusBar style="auto" />
        <Tab.Navigator
          screenOptions={({ route }) => ({
            headerShown: false,
            tabBarIcon: ({ focused, color, size }) => {
              let iconName: keyof typeof Ionicons.glyphMap = 'ellipse';
              if (route.name === 'Home') iconName = focused ? 'home' : 'home-outline';
              else if (route.name === 'Routes') iconName = focused ? 'bus' : 'bus-outline';
              else if (route.name === 'Saved') iconName = focused ? 'heart' : 'heart-outline';
              else if (route.name === 'Profile') iconName = focused ? 'person' : 'person-outline';
              return <Ionicons name={iconName} size={size} color={color} />;
            },
            tabBarActiveTintColor: '#1B8A4A',
            tabBarInactiveTintColor: '#9A9A9A',
            tabBarStyle: {
              height: 60,
              paddingBottom: 8,
              paddingTop: 4,
              borderTopWidth: 0.5,
              borderTopColor: '#ECECEA',
            },
            tabBarLabelStyle: {
              fontSize: 10,
              fontWeight: '600',
            },
          })}
        >
          <Tab.Screen name="Home" component={HomeScreen} />
          <Tab.Screen name="Routes" component={RoutesScreen} />
          <Tab.Screen name="Saved" component={SavedScreen} />
          <Tab.Screen name="Profile" component={ProfileScreen} />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
