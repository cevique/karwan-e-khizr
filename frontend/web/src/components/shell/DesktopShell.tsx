import { DesktopDock } from '../navigation/DesktopDock';
import { AuthScreen } from '../../screens/AuthScreen';
import { TicketsScreen } from '../../screens/TicketsScreen';
import { HomeScreen } from '../../screens/HomeScreen';
import { SearchScreen } from '../../screens/SearchScreen';
import { RoutesScreen } from '../../screens/RoutesScreen';
import { JourneyDetailScreen } from '../../screens/JourneyDetailScreen';
import { SavedScreen } from '../../screens/SavedScreen';
import { SettingsScreen } from '../../screens/SettingsScreen';
import { useApp } from '../../App';

export function DesktopShell() {
  const { state } = useApp();

  const renderScreen = () => {
    switch (state.screen) {
      case 'search':
        return <SearchScreen />;
      case 'routes':
        return <RoutesScreen />;
      case 'journey-detail':
        return <JourneyDetailScreen />;
      case 'saved':
        return <SavedScreen />;
      case 'settings':
        return <SettingsScreen />;
      case 'auth':
        return <AuthScreen />;
      case 'tickets':
        return <TicketsScreen />;
      default:
        return <HomeScreen />;
    }
  };

  return (
    <div style={styles.shell}>
      <DesktopDock />
      <div style={styles.main}>
        <div style={styles.content}>
          {renderScreen()}
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  shell: {
    display: 'flex',
    height: '100vh',
    width: '100vw',
    overflow: 'hidden',
  },
  main: {
    flex: 1,
    display: 'flex',
    justifyContent: 'center',
    overflow: 'hidden',
    background: 'var(--color-bg)',
  },
  content: {
    width: '100%',
    maxWidth: 1200,
    display: 'flex',
    overflow: 'hidden',
  },
};
