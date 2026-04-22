import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
} from 'react-native';
import { useLinkStore } from '../store/useLinkStore';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/AppNavigator';
import { Check } from 'lucide-react-native';

type SaveLinkScreenProps = NativeStackScreenProps<RootStackParamList, 'SaveLink'>;

const SaveLinkScreen = ({ route, navigation }: SaveLinkScreenProps) => {
  const sharedUrl = route.params?.url || '';
  const [url, setUrl] = useState(sharedUrl);
  const [selectedPathId, setSelectedPathId] = useState<number | null>(null);
  const [selectedSectionId, setSelectedSectionId] = useState<number | null>(null);

  const {
    paths,
    sections,
    isLoading,
    fetchPaths,
    fetchSections,
    saveLink,
  } = useLinkStore();

  useEffect(() => {
    fetchPaths();
  }, [fetchPaths]);

  useEffect(() => {
    if (selectedPathId) {
      fetchSections(selectedPathId);
      setSelectedSectionId(null);
    }
  }, [selectedPathId, fetchSections]);

  const handleSave = async () => {
    if (!url) {
      Alert.alert('Error', 'Please enter a URL');
      return;
    }
    if (!selectedSectionId) {
      Alert.alert('Error', 'Please select a section');
      return;
    }

    const success = await saveLink(url, selectedSectionId);
    if (success) {
      Alert.alert('Success', 'Link saved to Linkversity', [
        { text: 'OK', onPress: () => navigation.navigate('Home') },
      ]);
    } else {
      Alert.alert('Error', 'Failed to save link');
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.section}>
        <Text style={styles.label}>Link URL</Text>
        <TextInput
          style={styles.input}
          value={url}
          onChangeText={setUrl}
          placeholder="https://example.com"
          autoCapitalize="none"
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.label}>Select Path</Text>
        <View style={styles.optionsGrid}>
          {paths.map((path) => (
            <TouchableOpacity
              key={path.id}
              style={[
                styles.optionButton,
                selectedPathId === path.id && styles.optionButtonSelected,
              ]}
              onPress={() => setSelectedPathId(path.id)}
            >
              <Text
                style={[
                  styles.optionText,
                  selectedPathId === path.id && styles.optionTextSelected,
                ]}
                numberOfLines={1}
              >
                {path.title}
              </Text>
              {selectedPathId === path.id && <Check size={16} color="#fff" />}
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {selectedPathId && (
        <View style={styles.section}>
          <Text style={styles.label}>Select Section</Text>
          {isLoading && !sections[selectedPathId] ? (
            <ActivityIndicator color="#2563eb" />
          ) : (
            <View style={styles.optionsGrid}>
              {(sections[selectedPathId] || []).map((section) => (
                <TouchableOpacity
                  key={section.id}
                  style={[
                    styles.optionButton,
                    selectedSectionId === section.id && styles.optionButtonSelected,
                  ]}
                  onPress={() => setSelectedSectionId(section.id)}
                >
                  <Text
                    style={[
                      styles.optionText,
                      selectedSectionId === section.id && styles.optionTextSelected,
                    ]}
                    numberOfLines={1}
                  >
                    {section.title}
                  </Text>
                  {selectedSectionId === section.id && <Check size={16} color="#fff" />}
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>
      )}

      <TouchableOpacity
        style={[
          styles.saveButton,
          (!url || !selectedSectionId) && styles.saveButtonDisabled,
        ]}
        onPress={handleSave}
        disabled={isLoading || !url || !selectedSectionId}
      >
        {isLoading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.saveButtonText}>Save to Linkversity</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    padding: 20,
    gap: 24,
  },
  section: {
    gap: 8,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#475569',
  },
  input: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 12,
    borderRadius: 8,
    fontSize: 16,
    color: '#1e293b',
  },
  optionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  optionButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    maxWidth: '100%',
  },
  optionButtonSelected: {
    backgroundColor: '#2563eb',
    borderColor: '#2563eb',
  },
  optionText: {
    color: '#64748b',
    fontSize: 14,
  },
  optionTextSelected: {
    color: '#fff',
    fontWeight: '600',
  },
  saveButton: {
    backgroundColor: '#2563eb',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 20,
  },
  saveButtonDisabled: {
    backgroundColor: '#94a3b8',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
});

export default SaveLinkScreen;
