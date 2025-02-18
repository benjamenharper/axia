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
  const [results, setResults] = useState({
    properties: [],
    static_page_url: null,
    search_summary: null,
    location_overview: null
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recentSearches, setRecentSearches] = useState([]);
  const toast = useToast();
  
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const headerBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  useEffect(() => {
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
      window.open(`${process.env.REACT_APP_API_URL}${search.staticPageUrl}`, '_blank');
    } else {
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

    const apiUrl = `${process.env.REACT_APP_API_URL}/api/search`;
    console.log('Attempting API call to:', apiUrl);

    try {
      const response = await axios.post(apiUrl, {
        query: queryToUse
      }, {
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 30000, // 30 second timeout
      });
      
      console.log('API Response:', response.data);
      
      if (!response.data || typeof response.data !== 'object') {
        throw new Error('Invalid response format from API');
      }
      
      setResults(response.data);
      
      const newSearch = {
        query: queryToUse,
        timestamp: new Date().toISOString(),
        staticPageUrl: response.data.static_page_url
      };
      saveSearch(newSearch.query, newSearch.staticPageUrl);
    } catch (err) {
      console.error('Search error details:', {
        message: err.message,
        response: err.response,
        request: err.request,
        config: err.config
      });
      
      let errorMessage;
      if (err.response) {
        // Server responded with error
        errorMessage = err.response.data?.detail || err.response.data?.message || `Server error: ${err.response.status}`;
      } else if (err.request) {
        // Request made but no response
        errorMessage = 'No response from server. Please check your internet connection.';
      } else {
        // Error in request setup
        errorMessage = 'Error setting up the request. Please try again.';
      }
      
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
      <Flex direction="column" minH="100vh" bg={bgColor}>
        {/* Header */}
        <Box bg={headerBg} py={4} px={8} borderBottom="1px" borderColor={borderColor}>
          <Flex justify="space-between" align="center" maxW="1200px" mx="auto">
            <Heading
              size="lg"
              bgGradient="linear(to-r, blue.600, blue.400)"
              bgClip="text"
              letterSpacing="tight"
              fontWeight="bold"
            >
              AXIA Real Estate
            </Heading>
            <Button leftIcon={<AddIcon />} colorScheme="blue" onClick={handleNewSearch}>
              New Search
            </Button>
          </Flex>
        </Box>

        {/* Main Content */}
        <Box flex="1" py={8}>
          <Container maxW="1200px">
            <VStack spacing={8} align="stretch">
              {/* Search Form */}
              <form onSubmit={handleSubmit}>
                <FormControl>
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Describe your ideal property... (e.g., 'Find me a 3 bedroom house in Seattle under $800,000')"
                    size="lg"
                    bg="white"
                    _dark={{ bg: 'gray.700' }}
                  />
                  <Button
                    mt={4}
                    colorScheme="blue"
                    isLoading={loading}
                    type="submit"
                    width="full"
                  >
                    Search Properties
                  </Button>
                </FormControl>
              </form>

              {/* Recent Searches */}
              {recentSearches.length > 0 && !results.properties.length && (
                <Box>
                  <Text fontSize="lg" fontWeight="bold" mb={4}>Recent Searches</Text>
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                    {recentSearches.map((search, index) => (
                      <Box
                        key={index}
                        p={4}
                        bg="white"
                        _dark={{ bg: 'gray.700' }}
                        borderRadius="lg"
                        cursor="pointer"
                        onClick={() => handleRecentSearchClick(search)}
                        _hover={{ shadow: 'md' }}
                      >
                        <Text noOfLines={2}>{search.query}</Text>
                        <Flex align="center" mt={2} color="gray.500">
                          <TimeIcon mr={2} />
                          <Text fontSize="sm">
                            {new Date(search.timestamp).toLocaleDateString()}
                          </Text>
                        </Flex>
                      </Box>
                    ))}
                  </SimpleGrid>
                </Box>
              )}

              {/* Error Display */}
              {error && (
                <Alert status="error">
                  <AlertIcon />
                  <Box>
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                  </Box>
                </Alert>
              )}

              {/* Loading State */}
              {loading && (
                <Center p={8}>
                  <Spinner size="xl" />
                </Center>
              )}

              {/* Results Display */}
              {(results?.search_summary || '') && (
                <Box p={4} bg="white" _dark={{ bg: 'gray.700' }} borderRadius="lg">
                  <Text fontSize="lg" fontWeight="bold">Search Summary</Text>
                  <Text mt={2}>{results.search_summary}</Text>
                </Box>
              )}

              {(results?.location_overview || '') && (
                <Box p={4} bg="white" _dark={{ bg: 'gray.700' }} borderRadius="lg">
                  <Text fontSize="lg" fontWeight="bold">Location Overview</Text>
                  <div
                    dangerouslySetInnerHTML={{
                      __html: marked(results.location_overview || ''),
                    }}
                  />
                </Box>
              )}

              {(results?.properties?.length > 0) && (
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                  {results.properties.map((property, index) => (
                    <Box
                      key={index}
                      borderWidth="1px"
                      borderRadius="lg"
                      overflow="hidden"
                      bg="white"
                      _dark={{ bg: 'gray.700' }}
                    >
                      {property?.image_url && (
                        <Image
                          src={property.image_url}
                          alt={property.title || 'Property'}
                          height="200px"
                          width="100%"
                          objectFit="cover"
                        />
                      )}
                      <Box p={4}>
                        <Box mb={2}>
                          <Text fontSize="xl" fontWeight="semibold" noOfLines={2}>
                            {property?.title || 'No Title Available'}
                          </Text>
                          <Text fontSize="2xl" color="blue.500" fontWeight="bold">
                            ${(property?.price || 0).toLocaleString()}
                          </Text>
                        </Box>
                        <Text color="gray.500" mb={4} noOfLines={2}>
                          {property?.location || 'Location not available'}
                        </Text>
                        <Text noOfLines={3} mb={4}>
                          {property?.summary || 'No description available'}
                        </Text>
                        <Wrap spacing={2} mb={4}>
                          {(property?.features || []).map((feature, idx) => (
                            <WrapItem key={idx}>
                              <Badge colorScheme="blue">{feature}</Badge>
                            </WrapItem>
                          ))}
                        </Wrap>
                        {results?.static_page_url && (
                          <Link
                            href={`${process.env.REACT_APP_API_URL}${results.static_page_url}`}
                            isExternal
                            color="blue.500"
                          >
                            View Details <Icon as={ChakraExternalLinkIcon} mx="2px" />
                          </Link>
                        )}
                      </Box>
                    </Box>
                  ))}
                </SimpleGrid>
              )}
            </VStack>
          </Container>
        </Box>

        {/* Footer */}
        <Box bg={headerBg} py={4} borderTop="1px" borderColor={borderColor}>
          <Container maxW="1200px">
            <Text textAlign="center" color="gray.500">
              2024 AXIA Real Estate. All rights reserved.
            </Text>
          </Container>
        </Box>
      </Flex>
    </ChakraProvider>
  );
}

export default App;
