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
  const initialPathId = route.params?.pathId || null;
  
  const [url, setUrl] = useState(sharedUrl);
  const [selectedPathId, setSelectedPathId] = useState<number | null>(initialPathId);
  const [selectedSectionId, setSelectedSectionId] = useState<number | null>(null);
  
  const [isCreatingPath, setIsCreatingPath] = useState(false);
  const [newPathTitle, setNewPathTitle] = useState('');
  
  const [isCreatingSection, setIsCreatingSection] = useState(false);
  const [newSectionTitle, setNewSectionTitle] = useState('');

  const {
    paths,
    sections,
    isLoading,
    fetchPaths,
    fetchSections,
    saveLink,
    createPath,
    createSection,
  } = useLinkStore();

  useEffect(() => {
    fetchPaths(1);
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

  const handleCreatePath = async () => {
    if (!newPathTitle.trim()) return;
    const success = await createPath(newPathTitle.trim());
    if (success) {
      setNewPathTitle('');
      setIsCreatingPath(false);
      fetchPaths(1);
    } else {
      Alert.alert('Error', 'Failed to create path');
    }
  };

  const handleCreateSection = async () => {
    if (!newSectionTitle.trim() || !selectedPathId) return;
    const success = await createSection(newSectionTitle.trim(), selectedPathId);
    if (success) {
      setNewSectionTitle('');
      setIsCreatingSection(false);
      fetchSections(selectedPathId);
    } else {
      Alert.alert('Error', 'Failed to create section');
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
        <View style={styles.row}>
          <Text style={styles.label}>Select Path</Text>
          <TouchableOpacity onPress={() => setIsCreatingPath(!isCreatingPath)}>
            <Text style={styles.createText}>{isCreatingPath ? 'Cancel' : '+ New Path'}</Text>
          </TouchableOpacity>
        </View>

        {isCreatingPath && (
          <View style={styles.createForm}>
            <TextInput
              style={styles.smallInput}
              value={newPathTitle}
              onChangeText={setNewPathTitle}
              placeholder="Enter path title..."
              autoFocus
            />
            <TouchableOpacity 
              style={styles.createButton} 
              onPress={handleCreatePath}
              disabled={isLoading}
            >
              <Text style={styles.createButtonText}>Create</Text>
            </TouchableOpacity>
          </View>
        )}

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
          <View style={styles.row}>
            <Text style={styles.label}>Select Section</Text>
            <TouchableOpacity onPress={() => setIsCreatingSection(!isCreatingSection)}>
              <Text style={styles.createText}>{isCreatingSection ? 'Cancel' : '+ New Section'}</Text>
            </TouchableOpacity>
          </View>

          {isCreatingSection && (
            <View style={styles.createForm}>
              <TextInput
                style={styles.smallInput}
                value={newSectionTitle}
                onChangeText={setNewSectionTitle}
                placeholder="Enter section title..."
                autoFocus
              />
              <TouchableOpacity 
                style={styles.createButton} 
                onPress={handleCreateSection}
                disabled={isLoading}
              >
                <Text style={styles.createButtonText}>Create</Text>
              </TouchableOpacity>
            </View>
          )}

          {isLoading && !sections[selectedPathId] ? (
            <ActivityIndicator color="#ff8080" />
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
    fontSize: 14,
    fontWeight: 'bold',
    color: '#ff8080',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  createText: {
    fontSize: 14,
    color: '#ff8080',
    fontWeight: 'bold',
  },
  createForm: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  smallInput: {
    flex: 1,
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    fontSize: 14,
    color: '#1e293b',
  },
  createButton: {
    backgroundColor: '#ff8080',
    paddingHorizontal: 16,
    justifyContent: 'center',
    borderRadius: 8,
  },
  createButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
  input: {
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 16,
    borderRadius: 12,
    fontSize: 16,
    color: '#1e293b',
  },
  optionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  optionButton: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    backgroundColor: '#fff',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    maxWidth: '100%',
  },
  optionButtonSelected: {
    backgroundColor: '#ff8080',
    borderColor: '#ff8080',
  },
  optionText: {
    color: '#475569',
    fontSize: 15,
    fontWeight: '500',
  },
  optionTextSelected: {
    color: '#fff',
    fontWeight: 'bold',
  },
  saveButton: {
    backgroundColor: '#ff8080',
    padding: 18,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 20,
    shadowColor: '#ff8080',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
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
