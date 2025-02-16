import React, { useState, useEffect } from 'react';
import {
  ChakraProvider,
  Box,
  Container,
  VStack,
  Heading,
  Text,
  Input,
  Button,
  FormControl,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Center,
  Spinner,
  SimpleGrid,
  Image,
  Link,
  Icon,
  useToast,
  Wrap,
  WrapItem,
  Badge,
  Flex,
  Divider,
  useColorModeValue,
} from '@chakra-ui/react';
import { ExternalLinkIcon as ChakraExternalLinkIcon } from '@chakra-ui/icons';
import { AddIcon, TimeIcon } from '@chakra-ui/icons';
import axios from 'axios';
import { marked } from 'marked';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState({ properties: [], static_page_url: null, search_summary: null, location_overview: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recentSearches, setRecentSearches] = useState([]);
  const toast = useToast();
  
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const sidebarBg = useColorModeValue('white', 'gray.800');

  useEffect(() => {
    // Load recent searches from localStorage on component mount
    const savedSearches = localStorage.getItem('recentSearches');
    if (savedSearches) {
      setRecentSearches(JSON.parse(savedSearches));
    }
  }, []);

  const saveSearch = (query, staticPageUrl, timestamp = new Date().toISOString()) => {
    const newSearches = [
      { query, staticPageUrl, timestamp },
      ...recentSearches.filter(s => s.query !== query).slice(0, 9)
    ];
    setRecentSearches(newSearches);
    localStorage.setItem('recentSearches', JSON.stringify(newSearches));
  };

  const handleRecentSearchClick = (search) => {
    if (search.staticPageUrl) {
      // Open the static page in a new tab
      window.open(`http://localhost:8000${search.staticPageUrl}`, '_blank');
    } else {
      // Fallback to rerunning the search if no static page URL exists
      setSearchQuery(search.query);
      handleSubmit(null, search.query);
    }
  };

  const handleNewSearch = () => {
    setSearchQuery('');
    setResults({ properties: [], static_page_url: null, search_summary: null, location_overview: null });
    setError(null);
  };

  const handleSubmit = async (e, overrideQuery = null) => {
    if (e) e.preventDefault();
    const queryToUse = overrideQuery || searchQuery;
    
    if (!queryToUse.trim()) {
      setError('Please enter a search query');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${process.env.REACT_APP_API_URL}/api/search`, {
        query: queryToUse
      }, {
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      console.log('Received response:', response.data);
      
      setResults(response.data);
      
      // Add to recent searches
      const newSearch = {
        query: queryToUse,
        timestamp: new Date().toISOString(),
        staticPageUrl: response.data.static_page_url
      };
      saveSearch(newSearch.query, newSearch.staticPageUrl);
    } catch (err) {
      console.error('Search error:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'An error occurred while searching';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <ChakraProvider>
      <Flex h="100vh" bg={bgColor}>
        {/* Left Sidebar */}
        <Box
          w="300px"
          bg={sidebarBg}
          p={4}
          borderRight="1px"
          borderColor={borderColor}
          position="relative"
          zIndex="1"
        >
          <VStack spacing={6} align="stretch">
            {/* Site Title */}
            <Box>
              <Heading
                size="lg"
                bgGradient="linear(to-r, blue.600, blue.400)"
                bgClip="text"
                letterSpacing="tight"
                fontWeight="bold"
              >
                Axia
              </Heading>
              <Text color="gray.500" fontSize="sm" fontWeight="medium">
                AI Real Estate Search
              </Text>
            </Box>

            {/* Search Form */}
            <Box>
              <form onSubmit={handleSubmit} style={{ width: '100%' }}>
                <FormControl isInvalid={!!error}>
                  <Input
                    placeholder="Search properties..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    size="md"
                    borderRadius="md"
                    bg="white"
                    _focus={{
                      boxShadow: 'outline',
                      borderColor: 'blue.500',
                    }}
                  />
                  <Button
                    type="submit"
                    colorScheme="blue"
                    size="md"
                    width="full"
                    mt={2}
                    isLoading={loading}
                    loadingText="Searching..."
                  >
                    Search
                  </Button>
                  {error && (
                    <Alert status="error" mt={2} size="sm">
                      <AlertIcon />
                      <AlertDescription fontSize="sm">
                        {error}
                      </AlertDescription>
                    </Alert>
                  )}
                </FormControl>
              </form>
            </Box>
            
            {/* Recent Searches */}
            <Box>
              <Text fontWeight="bold" color="gray.500" fontSize="sm" mb={2}>
                Recent Searches
              </Text>
              <VStack spacing={2} align="stretch">
                {recentSearches.slice(0, 5).map((search, index) => {
                  const displayQuery = search.query
                    .split(' ')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(' ');
                  
                  return (
                    <Button
                      key={index}
                      variant="ghost"
                      justifyContent="flex-start"
                      leftIcon={search.staticPageUrl ? <ChakraExternalLinkIcon /> : <TimeIcon />}
                      onClick={() => handleRecentSearchClick(search)}
                      whiteSpace="normal"
                      textAlign="left"
                      h="auto"
                      py={2}
                      px={3}
                      _hover={{
                        bg: 'blue.50',
                      }}
                    >
                      <VStack align="start" spacing={1} width="100%">
                        <Text fontSize="sm" fontWeight="medium" color="blue.600" noOfLines={2}>
                          {displayQuery}
                        </Text>
                        <Text fontSize="xs" color="gray.500">
                          {new Date(search.timestamp).toLocaleString()}
                        </Text>
                      </VStack>
                    </Button>
                  );
                })}
                {recentSearches.length === 0 && (
                  <Text fontSize="sm" color="gray.500" textAlign="center" py={4}>
                    No recent searches
                  </Text>
                )}
              </VStack>
            </Box>
          </VStack>
        </Box>

        {/* Main Content Area */}
        <Box flex="1" p={8} bg="white">
          {loading ? (
            <Center h="100%">
              <Spinner size="xl" color="blue.500" thickness="4px" />
            </Center>
          ) : (
            <VStack spacing={6} align="stretch">
              {results.search_summary && (
                <Box>
                  <Heading size="md" mb={2}>Search Results</Heading>
                  <Text color="gray.600">{results.search_summary}</Text>
                </Box>
              )}
              
              {results.location_overview && (
                <Box>
                  <Heading size="md" mb={2}>Location Overview</Heading>
                  <Box
                    dangerouslySetInnerHTML={{
                      __html: marked.parse(results.location_overview)
                    }}
                    sx={{
                      'h1, h2, h3': {
                        fontSize: 'lg',
                        fontWeight: 'bold',
                        mt: 4,
                        mb: 2,
                        color: 'gray.700'
                      },
                      'p': {
                        mb: 3,
                        color: 'gray.600',
                        lineHeight: 'tall'
                      },
                      'ul, ol': {
                        pl: 4,
                        mb: 3,
                        color: 'gray.600'
                      },
                      'li': {
                        mb: 1
                      }
                    }}
                  />
                </Box>
              )}

              {results.properties && results.properties.length > 0 && (
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                  {results.properties.map((property) => (
                    <Box
                      key={property.id}
                      borderWidth="1px"
                      borderRadius="lg"
                      overflow="hidden"
                      bg="white"
                      shadow="md"
                    >
                      <Image
                        src={property.image_url}
                        alt={property.title}
                        h="200px"
                        w="full"
                        objectFit="cover"
                        fallback={
                          <Center h="200px" bg="gray.100">
                            <Text color="gray.500">No image available</Text>
                          </Center>
                        }
                      />
                      <Box p={4}>
                        <Heading size="md" mb={2}>
                          {property.title}
                        </Heading>
                        <Text color="blue.600" fontSize="2xl" mb={2}>
                          ${property.price.toLocaleString()}
                        </Text>
                        <Text color="gray.500" mb={2}>
                          {property.location}
                        </Text>
                        <Text mb={2}>{property.summary}</Text>
                        {property.features && property.features.length > 0 && (
                          <Wrap spacing={2} mt={2}>
                            {property.features.map((feature, index) => (
                              <WrapItem key={index}>
                                <Badge colorScheme="blue">{feature}</Badge>
                              </WrapItem>
                            ))}
                          </Wrap>
                        )}
                      </Box>
                    </Box>
                  ))}
                </SimpleGrid>
              )}
            </VStack>
          )}
        </Box>
      </Flex>
    </ChakraProvider>
  );
}

export default App;
